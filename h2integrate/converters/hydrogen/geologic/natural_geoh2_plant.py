import numpy as np
from attrs import field, define

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.converters.hydrogen.geologic.geoh2_baseclass import (
    GeoH2CostConfig,
    GeoH2CostBaseClass,
    GeoH2FinanceConfig,
    GeoH2FinanceBaseClass,
    GeoH2PerformanceConfig,
    GeoH2PerformanceBaseClass,
)


@define
class NaturalGeoH2PerformanceConfig(GeoH2PerformanceConfig):
    site_prospectivity: float = field()  # years
    initial_wellhead_flow: float = field()  # kg/hr
    gas_reservoir_size: float = field()  # tonnes


class NaturalGeoH2PerformanceModel(GeoH2PerformanceBaseClass):
    """
    An OpenMDAO component for modeling the performance of a natural geologic hydrogen plant.
    Contains parameters specific to natural geologic hydrogen sub-model.
    yada yada yada

    Inputs:
        -yada yada yada
    Outputs:
        -yada yada yada
    """

    def setup(self):
        self.config = NaturalGeoH2PerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        super().setup()

        self.add_input("site_prospectivity", units=None, val=self.config.site_prospectivity)
        self.add_input("initial_wellhead_flow", units="kg/h", val=self.config.initial_wellhead_flow)
        self.add_input("gas_reservoir_size", units="t", val=self.config.gas_reservoir_size)

        self.add_output("wellhead_h2_conc", units="percent")
        self.add_output("lifetime_wellhead_flow", units="kg/h")
        self.add_output("hydrogen_accumulated", units="kg/h", shape=(8760,))

    def compute(self, inputs, outputs):
        # Calculate expected wellhead h2 concentration from prospectivity
        prospectivity = inputs["site_prospectivity"]
        wh_h2_conc = 58.92981751 * prospectivity**2.460718753  # percent

        # Calculated average wellhead gas flow over well lifetime
        init_wh_flow = inputs["initial_wellhead_flow"]
        lifetime = int(inputs["well_lifetime"][0])
        res_size = inputs["gas_reservoir_size"]
        avg_wh_flow = min(init_wh_flow, res_size / lifetime * 1000 / 8760)

        # Calculate hydrogen flow out from accumulated gas
        h2_accum = wh_h2_conc / 100 * avg_wh_flow

        # Parse outputs
        outputs["wellhead_h2_conc"] = wh_h2_conc
        outputs["lifetime_wellhead_flow"] = avg_wh_flow
        outputs["hydrogen_accumulated"] = h2_accum
        outputs["hydrogen"] = h2_accum


@define
class NaturalGeoH2CostConfig(GeoH2CostConfig):
    pass


class NaturalGeoH2CostModel(GeoH2CostBaseClass):
    """
    An OpenMDAO component for modeling the cost of a natural geologic hydrogen plant.
    Contains parameters specific to natural geologic hydrogen sub-model.
    yada yada yada

    Inputs:
        -yada yada yada
    Outputs:
        -yada yada yada
    """

    def setup(self):
        self.config = NaturalGeoH2CostConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()

    def compute(self, inputs, outputs):
        # Calculate total capital cost per well (successful or unsuccessful)
        drill = inputs["test_drill_cost"]
        permit = inputs["permit_fees"]
        acreage = inputs["acreage"]
        rights_acre = inputs["rights_cost"]
        cap_well = drill + permit + acreage * rights_acre

        # Calculate total capital cost per SUCCESSFUL well
        completion = inputs["completion_cost"]
        success = inputs["success_chance"]
        bare_capex = cap_well / success * 100 + completion
        outputs["bare_capital_cost"] = bare_capex

        # Parse in opex
        fopex = inputs["fixed_opex"]
        vopex = inputs["variable_opex"]
        outputs["Fixed_OpEx"] = fopex
        outputs["Variable_OpEx"] = vopex
        production = np.sum(inputs["hydrogen"])
        outputs["OpEx"] = fopex + vopex * np.sum(production)

        # Apply cost multipliers to bare erected cost via NETL-PUB-22580
        contracting_costs = bare_capex * 0.20
        epc_cost = bare_capex + contracting_costs
        contingency_costs = epc_cost * 0.50
        total_plant_cost = epc_cost + contingency_costs
        preprod_cost = fopex * 0.50
        total_overnight_cost = total_plant_cost + preprod_cost
        tasc_toc_multiplier = 1.10  # simplifying for now
        total_as_spent_cost = total_overnight_cost * tasc_toc_multiplier
        outputs["CapEx"] = total_as_spent_cost


@define
class NaturalGeoH2FinanceConfig(GeoH2FinanceConfig):
    pass


class NaturalGeoH2FinanceModel(GeoH2FinanceBaseClass):
    """
    An OpenMDAO component for modeling the financing of a natural geologic hydrogen plant.
    Contains parameters specific to natural geologic hydrogen sub-model.
    yada yada yada

    Inputs:
        -yada yada yada
    Outputs:
        -yada yada yada
    """

    def setup(self):
        self.config = NaturalGeoH2FinanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "finance")
        )
        super().setup()

    def compute(self, inputs, outputs):
        # Calculate fixed charge rate via NETL-PUB-22580
        lifetime = int(inputs["well_lifetime"][0])
        etr = 0.2574  # effective tax rate
        atwacc = 0.0473  # after-tax weighted average cost of capital - see NETL Exhibit 3-2
        dep_n = 1 / lifetime  # simplifying the IRS tax depreciation tables to avoid lookup
        crf = (
            atwacc * (1 + atwacc) ** lifetime / ((1 + atwacc) ** lifetime - 1)
        )  # capital recovery factor
        dep = crf * np.sum(dep_n / np.power(1 + atwacc, np.linspace(1, lifetime, lifetime)))
        fcr = crf / (1 - etr) - etr * dep / (1 - etr)

        # Calculate levelized cost of geoH2
        capex = inputs["CapEx"]
        fopex = inputs["Fixed_OpEx"]
        vopex = inputs["Variable_OpEx"]
        production = np.sum(inputs["hydrogen"])
        lcoh = (capex * fcr + fopex) / production + vopex
        outputs["LCOH"] = lcoh
        outputs["LCOH_capex"] = (capex * fcr) / production
        outputs["LCOH_fopex"] = fopex / production
        outputs["LCOH_vopex"] = vopex
