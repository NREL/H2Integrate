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


try:
    from mcm import echem_mcc
except ImportError:
    echem_mcc = None


@define
class DOCPerformanceConfig(MarineCarbonCapturePerformanceConfig):
    """Extended configuration for Direct Ocean Capture (DOC) performance model.

    Attributes:
        E_HCl (float): Energy required per mole of HCl produced (kWh/mol).
        E_NaOH (float): Energy required per mole of NaOH produced (kWh/mol).
        y_ext (float): CO2 extraction efficiency (unitless fraction).
        y_pur (float): CO2 purity in the product stream (unitless fraction).
        y_vac (float): Vacuum pump efficiency (unitless fraction).
        frac_ed_flow (float): Fraction of intake flow directed to electrodialysis (unitless).
        temp_C (float): Temperature of input seawater (°C).
        sal (float): Salinity of seawater (ppt).
        dic_i (float): Initial dissolved inorganic carbon (mol/L).
        pH_i (float): Initial pH of seawater.
        initial_tank_volume_m3 (float): Initial volume of the tank (m³).
    """

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

    Extends:
        MarineCarbonCapturePerformanceBaseClass

    Computes:
        - Hourly CO2 capture rate (t/h)
        - Annual CO2 capture (t/year)
    """

    def initialize(self):
        super().initialize()
        if echem_mcc is None:
            raise ImportError(
                "The `mcm` package is required. Install it via:\n"
                "pip install git+https://github.com/NREL/MarineCarbonManagement.git"
            )

    def setup(self):
        self.config = DOCPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        super().setup()
        self.add_output(
            "plant_mCC_capacity_mtph",
            val=0.0,
            units="t/h",
            desc="Theoretical maximum CO₂ capture (t/h)",
        )
        self.add_output(
            "total_tank_volume_m3",
            val=0.0,
            units="m**3",
        )

    def compute(self, inputs, outputs):
        ED_inputs = echem_mcc.ElectrodialysisInputs(
            P_ed1=self.config.power_single_ed_w,
            Q_ed1=self.config.flow_rate_single_ed_m3s,
            N_edMin=self.config.number_ed_min,
            N_edMax=self.config.number_ed_max,
            E_HCl=self.config.E_HCl,
            E_NaOH=self.config.E_NaOH,
            y_ext=self.config.y_ext,
            y_pur=self.config.y_pur,
            y_vac=self.config.y_vac,
            frac_EDflow=self.config.frac_ed_flow,
            use_storage_tanks=self.config.use_storage_tanks,
            store_hours=self.config.store_hours,
        )

        co_2_outputs, range_outputs, ed_outputs = echem_mcc.run_electrodialysis_physics_model(
            power_profile_w=inputs["electricity_in"],
            initial_tank_volume_m3=self.config.initial_tank_volume_m3,
            electrodialysis_config=ED_inputs,
            pump_config=echem_mcc.PumpInputs(),
            seawater_config=echem_mcc.SeaWaterInputs(
                sal=self.config.sal,
                tempC=self.config.temp_C,
                dic_i=self.config.dic_i,
                pH_i=self.config.pH_i,
            ),
            save_outputs=True,
            save_plots=True,
            output_dir="./output/",  # TODO: how do I change this to be based on folder_output in driver_config.yaml?
            plot_range=[3910, 4030],
        )

        outputs["co2_capture_rate_mt"] = ed_outputs.ED_outputs["mCC"]
        outputs["co2_capture_mtpy"] = ed_outputs.mCC_yr
        outputs["total_tank_volume_m3"] = range_outputs.V_aT_max + range_outputs.V_bT_max
        outputs["plant_mCC_capacity_mtph"] = max(range_outputs.S1["mCC"])


@define
class DOCCostModelConfig(BaseConfig):
    """Configuration for the DOC cost model.

    Attributes:
        infrastructure_type (str): Type of infrastructure (e.g., "desal", "swCool", "new"").
    """

    infrastructure_type: str = field()


class DOCCostModel(MarineCarbonCaptureCostBaseClass):
    """OpenMDAO component for computing capital (CapEx) and operational (OpEx) costs of a
        direct ocean capture (DOC) system.

    Computes:
        - CapEx (USD)
        - OpEx (USD/year)
    """

    def initialize(self):
        super().initialize()
        if echem_mcc is None:
            raise ImportError(
                "The `mcm` package is required. Install it via:\n"
                "pip install git+https://github.com/NREL/MarineCarbonManagement.git"
            )

    def setup(self):
        super().setup()
        self.performance_config = DOCPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        self.config = DOCCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

        # TODO: figure out how to share this input between finance and cost model. it's an output of performance model
        self.add_input(
            "total_tank_volume_m3",
            val=0.0,
            units="m**3",
        )

    def compute(self, inputs, outputs):
        ED_inputs = echem_mcc.ElectrodialysisInputs(
            P_ed1=self.performance_config.power_single_ed_w,
            Q_ed1=self.performance_config.flow_rate_single_ed_m3s,
            N_edMin=self.performance_config.number_ed_min,
            N_edMax=self.performance_config.number_ed_max,
            E_HCl=self.performance_config.E_HCl,
            E_NaOH=self.performance_config.E_NaOH,
            y_ext=self.performance_config.y_ext,
            y_pur=self.performance_config.y_pur,
            y_vac=self.performance_config.y_vac,
            frac_EDflow=self.performance_config.frac_ed_flow,
            use_storage_tanks=self.performance_config.use_storage_tanks,
            store_hours=self.performance_config.store_hours,
        )

        res = echem_mcc.electrodialysis_cost_model(
            echem_mcc.ElectrodialysisCostInputs(
                electrodialysis_inputs=ED_inputs,
                mCC_yr=inputs["co2_capture_mtpy"],
                total_tank_volume=inputs["total_tank_volume_m3"],
                infrastructure_type=self.config.infrastructure_type,
                max_theoretical_mCC=inputs["plant_mCC_capacity_mtph"],
            )
        )

        # Calculate CapEx
        outputs["CapEx"] = res.initial_capital_cost
        outputs["OpEx"] = res.yearly_operational_cost


class DOCFinance(om.ExplicitComponent):
    """OpenMDAO component to compute the levelized cost of CO2 (LCOC) for DOC systems.

    Inputs:
        CapEx (float): Capital expenditure (USD).
        OpEx (float): Operating expenditure (USD/year).
        co2_capture_mtpy (float): Annual CO2 capture (t/year).

    Outputs:
        LCOC (float): Levelized cost of CO2 captured (USD/t).
    """

    # TODO: further develop LCOC metric using LCOE for electricity costs and outputs from cost and performance model

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("CapEx", val=0.0, units="USD", desc="Capital expenditure (USD)")
        self.add_input("OpEx", val=0.0, units="USD/year", desc="Operational expenditure (USD/year)")
        self.add_input("co2_capture_mtpy", units="t/year", desc="Annual CO2 capture (t/year)")

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
        outputs["LCOC"] = total_annual_cost / np.sum(inputs["co2_capture_mtpy"])
