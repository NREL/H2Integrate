import mcm
import numpy as np
import openmdao.api as om
import numpy_financial as npf
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.converters.marine_carbon_capture.marine_carbon_capture_baseclass import (
    MarineCarbonCaptureCostBaseClass,
    MarineCarbonCapturePerformanceConfig,
    MarineCarbonCapturePerformanceBaseClass,
)


@define
class DOCPerformanceConfig(MarineCarbonCapturePerformanceConfig):
    E_HCl: float = field()
    E_NaOH: float = field()
    y_ext: float = field()
    y_pur: float = field()
    y_vac: float = field()
    frac_ed_flow: float = field()
    temp_C: float = field()
    sal: float = field()
    dic_i: float = field()
    pH_i: float = field()
    initial_tank_volume_m3: float = field()


class DOCPerformanceModel(MarineCarbonCapturePerformanceBaseClass):
    """
    An OpenMDAO component for modeling the performance of a Direct Ocean Capture (DOC) plant.
    This model extends the MarineCarbonCapturePerformanceBaseClass to
    implement specific performance calculations for DOC technology.

    Inputs:
        - E_HCl: Energy consumption for HCl in kWh/mol
        - E_NaOH: Energy consumption for NaOH in kWh/mol
        - y_ext: CO2 extraction efficiency as a fraction (unitless)
        - y_pur: Purity of CO2 extracted as a fraction (unitless)
        - y_vac: Vacuum efficiency as a fraction (unitless)
        - frac_ed_flow: Fraction of intake flow directed to ED units (unitless)
        - temp_C: Temperature in degrees Celsius
        - sal: Salinity in parts per thousand (ppt)
        - dic_i: Initial dissolved inorganic carbon concentration in mol/L
        - pH_i: Initial pH value (unitless)
        - initial_tank_volume_m3: Initial volume of the tank in cubic meters (m^3)
    """

    def setup(self):
        self.config = DOCPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        super().setup()

        # Add specific inputs for DOC performance model
        self.add_input("E_HCl", val=self.config.E_HCl, units="kW*h/mol")
        self.add_input("E_NaOH", val=self.config.E_NaOH, units="kW*h/mol")
        self.add_input("y_ext", val=self.config.y_ext, units="unitless")
        self.add_input("y_pur", val=self.config.y_pur, units="unitless")
        self.add_input("y_vac", val=self.config.y_vac, units="unitless")
        self.add_input("frac_ed_flow", val=self.config.frac_ed_flow, units="unitless")
        self.add_input("temp_C", val=self.config.temp_C, units="degC")
        self.add_input("sal", val=self.config.sal, units="ppt")
        self.add_input("dic_i", val=self.config.dic_i, units="mol/L")
        self.add_input("pH_i", val=self.config.pH_i, units="unitless")
        self.add_input(
            "initial_tank_volume_m3", val=self.config.initial_tank_volume_m3, units="m**3"
        )

    def compute(self, inputs, outputs):
        ED_inputs = mcm.capture.echem_mcc.ElectrodialysisInputs(
            P_ed1=inputs["power_single_ed_w"],
            Q_ed1=inputs["flow_rate_single_ed_m3s"],
            N_edMin=inputs["number_ed_min"],
            N_edMax=inputs["num_ed_max"],
            E_HCl=inputs["E_HCl"],
            E_NaOH=inputs["E_NaOH"],
            y_ext=inputs["y_ext"],
            y_pur=inputs["y_pur"],
            y_vac=inputs["y_vac"],
            frac_EDflow=inputs["frac_EDflow"],
            use_storage_tanks=inputs["use_storage_tanks"],
            store_hours=inputs["store_hours"],
        )

        co_2_outputs, range_outputs, ed_outputs = (
            mcm.capture.echem_mcc.run_electrodialysis_physics_model(
                power_profile_w=inputs["electricity_in"],
                initial_tank_volume_m3=inputs["initial_tank_volume_m3"],
                electrodialysis_config=ED_inputs,
                pump_config=mcm.capture.echem_mcc.PumpInputs(),
                seawater_config=mcm.capture.echem_mcc.SeaWaterInputs(
                    sal=inputs["sal"],
                    tempC=inputs["temp_C"],
                    dic_i=inputs["dic_i"],
                    pH_i=inputs["pH_i"],
                ),
                save_outputs=True,
                save_plots=True,
                plot_range=[3910, 4030],
            )
        )

        outputs["co2_capture_rate_mtph"] = co_2_outputs.mCC_yr


@define
class DOCCostModelConfig(BaseConfig):
    average_co2_capture_mtpy: float = field()
    cost_per_kw: float = field()


class DOCCostModel(MarineCarbonCaptureCostBaseClass):
    """
    An OpenMDAO component that calculates the capital expenditure (CapEx) for a wind plant.

    Just a placeholder for now, but can be extended with more detailed cost models.
    """

    def initialize(self):
        super().initialize()

    def setup(self):
        super().setup()
        self.config = DOCCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

    def compute(self, inputs, outputs):
        cost_per_kw = self.config.cost_per_kw

        # Calculate CapEx
        total_capacity_kw = self.config.average_co2_capture_mtpy
        outputs["CapEx"] = total_capacity_kw * cost_per_kw
        outputs["OpEx"] = 0.03 * total_capacity_kw * cost_per_kw  # placeholder scalar value


class DOCFinance(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("CapEx", val=0.0, units="USD", desc="Capital expenditure")
        self.add_input("OpEx", val=0.0, units="USD/year", desc="Operational expenditure")
        self.add_input(
            "average_co2_capture_mtpy", units="t/year", desc="Average annual CO2 capture"
        )

        self.add_output(
            "LCOC",
            val=0.0,
            units="USD/t",
            desc="Levelized cost of CO2 captured",
        )

    def compute(self, inputs, outputs):
        # Financial parameters
        project_lifetime = self.options["plant_config"]["plant"]["plant_life"]  # years
        discount_rate = self.options["plant_config"]["finance_parameters"][
            "discount_rate"
        ]  # annual discount rate

        # Calculate the annualized CapEx using the present value of an annuity formula
        annualized_CapEx = npf.pmt(discount_rate, project_lifetime, -inputs["CapEx"])

        # Total annual cost
        total_annual_cost = annualized_CapEx + inputs["OpEx"]

        # Calculate the levelized cost of CO2 captured
        outputs["LCOC"] = total_annual_cost / np.sum(inputs["average_co2_capture_mtpy"])
