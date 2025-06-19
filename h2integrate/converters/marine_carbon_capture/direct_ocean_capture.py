import numpy as np
import openmdao.api as om
import numpy_financial as npf
from mcm import echem_mcc
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
            plot_range=[3910, 4030],
        )

        outputs["co2_capture_rate_mtph"] = ed_outputs.ED_outputs["mCC"]
        outputs["average_co2_capture_mtpy"] = ed_outputs.mCC_yr


@define
class DOCCostModelConfig(BaseConfig):
    average_co2_capture_mtpy: float = field()
    total_tank_volume_m3: float = field()
    infrastructure_type: str = field()
    plant_mCC_capacity_mtpy: float = field()


class DOCCostModel(MarineCarbonCaptureCostBaseClass):
    """
    An OpenMDAO component that calculates the capital expenditure (CapEx) for a direct
    ocean capture (DOC) plant.
    """

    def initialize(self):
        super().initialize()

    def setup(self):
        super().setup()
        self.performance_config = DOCPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        self.config = DOCCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
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
                mCC_yr=self.config.average_co2_capture_mtpy,
                total_tank_volume=self.config.total_tank_volume_m3,
                infrastructure_type=self.config.infrastructure_type,
                max_theoretical_mCC=self.config.plant_mCC_capacity_mtpy,
            )
        )

        # Calculate CapEx
        outputs["CapEx"] = res.initial_capital_cost
        outputs["OpEx"] = res.yearly_operational_cost


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
