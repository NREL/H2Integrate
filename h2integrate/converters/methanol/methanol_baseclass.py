import numpy as np
import pandas as pd
import openmdao.api as om


class MethanolBaseClass(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling a methanol plant.
    A base class used to further define Performance, Cost, and Finacnce components.

    Attributes:
        - dec_table_inputs (list of lists):
            Formatted table of inputs/outputs to declare using the "declare_from_table" method
            See examples below - first row is column headers, following rows are inputs/outputs
        - values (dict): key-value pairs to go with dec_table_inputs, in which
            keys: Names of variables to assign values to
            values: Values to assign
            Values do not have to be given for every input/output in dec_table_inputs,
            they will be assigned a value of zero if they are not included in values
        - dec_table (pandas DataFrame):
            Pandas-formatted table of inputs/outputs that have been added to the OpenMDAO component
    """

    dec_table_inputs: list
    values: dict
    dec_table: pd.DataFrame

    def declare_from_table(self, add_dec_table_inputs=None, add_values=None):
        """
        Declare inputs/outputs from a table, either initialized with zeros or with values from dict

        Arguments:
            - add_dec_table_inputs (list of lists):
                Additional inputs/outputs to assign in addition to self.dec_table_inputs
            - add_values (dict):
                Additional values to assign to the inputs/outputs in add_dec_table_inputs
        """

        # Convert dec_table to dataframe for easy references
        dec_table = pd.DataFrame(self.dec_table_inputs[1:], columns=self.dec_table_inputs[0])
        if add_dec_table_inputs:
            add_dec_table = pd.DataFrame(add_dec_table_inputs[1:], columns=add_dec_table_inputs[0])
            dec_table = pd.concat([dec_table, add_dec_table])
        self.dec_table = dec_table

        # Combine any additional values from those already defined
        values = self.values
        if add_values:
            for key, value in add_values.items():
                values[key] = value
            self.values = values

        # Add each row of the dec_table as an input or output
        for dec in self.dec_table.itertuples():
            # If a value was given for the given input/output name, initialize with that value
            if dec.name in list(values.keys()):
                value = self.values[dec.name]
            # Otherwise initialize as zero(s)
            else:
                if dec.len == 1:
                    value = 0.0
                else:
                    value = np.zeros(int(dec.len))

            # Add inputs/outputs to OpenMDAO component
            if dec.type == "in":
                self.add_input(dec.name, val=value, shape_by_conn=dec.conn, units=dec.unit)
            elif dec.type == "out":
                self.add_output(dec.name, val=value, shape_by_conn=dec.conn, units=dec.unit)


class MethanolPerformanceBaseClass(MethanolBaseClass):
    """
    An OpenMDAO component for modeling the performance of a methanol plant.
    Computes annual methanol and co-product production, feedstock consumption, and emissions
    based on plant capacity and capacity factor.

    Inputs:
        - plant_capacity_kgpy: methanol produciton capacity in kg/year
        - capacity_factor: fractional factor of full production capacity that is realized
        - XXX_produce_ratio: ratio of XXX produced to kg methanol produced
        - XXX_consume_ratio: ratio of XXX consumed to kg methanol produced
        - XXX_emit_ratio: ratio of XXX emitted to kg methanol produced
    Outputs:
        - XXX_production: XXX production
        - XXX_consumption: XXX consumption
        - XXX_emission: XXX emission
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        # Make table of all inputs and outputs to declare
        self.dec_table_inputs = [
            ["type", "len", "conn", "unit", "name"],
            ["in", 1, False, "kg/year", "plant_capacity_kgpy"],
            ["in", 1, False, None, "capacity_factor"],
            ["in", 1, False, "kg/kg", "co2e_emit_ratio"],
            ["in", 1, False, "kg/kg", "h2o_consume_ratio"],
            ["in", 1, False, "kg/kg", "h2_consume_ratio"],
            ["in", 1, False, "kg/kg", "co2_consume_ratio"],
            ["in", 1, False, "kW*h/kg", "elec_consume_ratio"],
            ["out", 8760, False, "kg/h", "methanol_production"],
            ["out", 8760, False, "kg/h", "co2e_emissions"],
            ["out", 8760, False, "kg/h", "h2o_consumption"],
            ["out", 8760, False, "kg/h", "h2_consumption"],
            ["out", 8760, False, "kg/h", "co2_consumption"],
            ["out", 8760, False, "kW*h/h", "elec_consumption"],
        ]
        # Define any non-zero default values
        self.values = {
            "plant_capacity_kgpy": 100000000.0,
            "capacity_factor": 0.85,
        }

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implemented and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")


class MethanolCostBaseClass(MethanolBaseClass):
    """
    An OpenMDAO component for modeling the cost of a methanol plant.
    Includes CapEx, OpEx (fixed and variable), feedstock costs, and co-product credits.

    Uses NETL power plant quality guidelines quantity of "total overnight cost" (TOC) for CapEx
    NETL-PUB-22580 doi.org/10.2172/1567736
    Splits OpEx into Fixed and Variable (variable scales with capacity factor, fixed does not)

    Inputs:
        toc_kg_y: total overnight cost (TOC) slope - multiply by plant_capacity_kgpy to get CapEx
        foc_kg_y^2: fixed operating cost slope - multiply by plant_capacity_kgpy to get Fixed_OpEx
        voc_kg: variable operating cost - multiple by methanol_production to get Variable_OpEx
        plant_capacity_kgpy: shared input, see MethanolPerformanceBaseClass
        methanol_production: promoted output from MethanolPerformanceBaseClass
    Outputs:
        CapEx: all methanol plant capital expenses in the form of total overnight cost (TOC)
        OpEx: all methanol plant operating expenses (fixed and variable)
        Fixed_OpEx: all methanol plant fixed operating expenses (do NOT vary with production rate)
        Variable_OpEx: all methanol plant variable operating expenses (vary with production rate)
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        # Make table of all inputs and outputs to declare
        self.dec_table_inputs = [
            ["type", "len", "conn", "unit", "name"],
            ["in", 1, False, "USD/kg/year", "toc_kg_y"],
            ["in", 1, False, "USD/kg/year**2", "foc_kg_y^2"],  # fixed operating cost slope
            ["in", 1, False, "USD/kg", "voc_kg"],  # variable operating cost
            ["in", 1, False, "kg/year", "plant_capacity_kgpy"],
            ["in", 1, False, "USD/kW/h", "electricity_price"],
            ["in", 1, False, "USD/kg", "hydrogen_price"],
            ["in", 8760, False, "kW*h/h", "electricity_consumption"],
            ["in", 8760, False, "kg/h", "hydrogen_consumption"],
            ["in", 8760, False, "kg/h", "methanol_production"],
            ["out", 1, False, "USD", "CapEx"],
            ["out", 1, False, "USD/year", "OpEx"],
            ["out", 1, False, "USD/year", "Fixed_OpEx"],
            ["out", 1, False, "USD/year", "Variable_OpEx"],
        ]
        # Define any non-zero default values
        self.values = {
            "plant_capacity_kgpy": 100000000.0,
        }

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")


class MethanolFinanceBaseClass(MethanolBaseClass):
    """
    An OpenMDAO component for modeling the financing of a methanol plant.
    Includes CapEx, OpEx (fixed and variable), feedstock costs, and co-product credits.

    Uses NETL power plant quality guidelines' total as-spent cost (TASC) multiplier for capex
    Capex expenses are annualized using a fixed charge rate also taken from NETL guidelines
    NETL-PUB-22580 doi.org/10.2172/1567736

    Inputs:
        CapEx: promoted output from MethanolCostBaseClass
        OpEx: promoted output from MethanolCostBaseClass
        Fixed_OpEx: promoted output from MethanolCostBaseClass
        Variable_OpEx: promoted output from MethanolCostBaseClass
        tasc_toc_multiplier: calculates TASC (total as-spent cost) from CapEx
        fixed_charge_rate: calculates annualized CapEx finance payments from TASC
        methanol_production: promoted output from MethanolPerformanceBaseClass
    Outputs:
        LCOM: levelized cost of methanol
        LCOM_meoh: portion of the LCOM from the methanol plant itself (no feedstocks)
        LCOM_meoh_capex: portion of the LCOM_meoh from capital expenses
        LCOM_meoh_fopex: portion of the LCOM_meoh from fixed operating expenses
        LCOM_meoh_vopex: portion of the LCOM_meoh from variable operating expenses
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        # Make table of all inputs and outputs to declare
        self.dec_table_inputs = [
            ["type", "len", "conn", "unit", "name"],
            ["in", 1, False, "USD", "CapEx"],
            ["in", 1, False, "USD/year", "OpEx"],
            ["in", 1, False, "USD/year", "Fixed_OpEx"],
            ["in", 1, False, "USD/year", "Variable_OpEx"],
            ["in", 1, False, None, "tasc_toc_multiplier"],
            ["in", 1, False, None, "fixed_charge_rate"],
            ["in", 8760, False, "kg/h", "methanol_production"],
            ["out", 1, False, "USD/kg", "LCOM"],
            ["out", 1, False, "USD/kg", "LCOM_meoh"],
            ["out", 1, False, "USD/kg", "LCOM_meoh_capex"],
            ["out", 1, False, "USD/kg", "LCOM_meoh_fopex"],
            ["out", 1, False, "USD/kg", "LCOM_meoh_vopex"],
        ]
        # Sources in NETL-PUB-22580: Exhibit 3-5 and Exhibit 3-7
        self.values = {
            "fixed_charge_rate": 0.0707,
            "tasc_toc_multiplier": 1.093,
        }

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")
