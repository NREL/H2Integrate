from attrs import field, define

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.converters.co2.marine.marine_carbon_capture_baseclass import (
    MarineCarbonCaptureCostBaseClass,
    MarineCarbonCapturePerformanceConfig,
    MarineCarbonCapturePerformanceBaseClass,
)


try:
    from mcm.capture import echem_oae
except ImportError:
    echem_oae = None


def setup_ocean_alkalinity_enhancement_inputs(config):
    """Helper function to set up ocean alkalinity enhancement inputs from the configuration."""
    return echem_oae.OAEInputs(
        N_edMin=config.number_ed_min,
        N_edMax=config.number_ed_max,
        assumed_CDR_rate=config.assumed_CDR_rate,
        Q_edMax=config.max_ed_system_flow_rate_m3s,
        frac_baseFlow=config.frac_base_flow,
        use_storage_tanks=config.use_storage_tanks,
        store_hours=config.store_hours,
        acid_disposal_method=config.acid_disposal_method,
    )


@define
class OAEPerformanceConfig(MarineCarbonCapturePerformanceConfig):
    """Extended configuration for Ocean Alkalinity Enhancement (OAE) performance model.

    Attributes:
        assumed_CDR_rate (float): Mole of CO2 per mole of NaOH (unitless).
        frac_base_flow (float): Fraction of base flow in the system (unitless).
        max_ed_system_flow_rate_m3s (float): Maximum flow rate through the ED system (m³/s).
        initial_temp_C (float): Temperature of input seawater (°C).
        initial_salinity_ppt (float): Initial salinity of seawater (ppt).
        initial_dic_mol_per_L (float): Initial dissolved inorganic carbon (mol/L).
        initial_pH (float): Initial pH of seawater.
        initial_tank_volume_m3 (float): Initial volume of the tank (m³).
        acid_disposal_method (str): Method for acid disposal.
    """

    assumed_CDR_rate: float = field()
    frac_base_flow: float = field()
    max_ed_system_flow_rate_m3s: float = field()
    initial_temp_C: float = field()
    initial_salinity_ppt: float = field()
    initial_dic_mol_per_L: float = field()
    initial_pH: float = field()
    initial_tank_volume_m3: float = field()
    acid_disposal_method: str = field()


class OAEPerformanceModel(MarineCarbonCapturePerformanceBaseClass):
    """OpenMDAO component for modeling Ocean Alkalinity Enhancement (OAE) performance.

    Extends:
        MarineCarbonCapturePerformanceBaseClass

    Computes:
        - co2_capture_rate_mt: Hourly CO₂ capture rate in metric tons.
        - co2_capture_mtpy: Annual CO₂ captured in metric tons per year.

    Notes:
        This component requires the mcm.capture.echem_oae module for calculations.
    """

    def initialize(self):
        super().initialize()
        if echem_oae is None:
            raise ImportError(
                "The `mcm` package is required. Install it via:\n"
                "pip install git+https://github.com/NREL/MarineCarbonManagement.git"
            )

    def setup(self):
        self.config = OAEPerformanceConfig.from_dict(
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
            "alkaline_seawater_flow_rate",
            shape=8760,
            val=0.0,
            units="m**3/s",
            desc="Alkaline seawater flow rate (m³/s)",
        )
        self.add_output(
            "alkaline_seawater_pH", val=0.0, shape=8760, desc="pH of the alkaline seawater"
        )
        self.add_output(
            "alkaline_seawater_dic",
            val=0.0,
            shape=8760,
            units="mol/L",
            desc="Dissolved inorganic carbon concentration in the alkaline seawater",
        )
        self.add_output(
            "alkaline_seawater_ta",
            val=0.0,
            shape=8760,
            units="mol/L",
            desc="Total alkalinity of the alkaline seawater",
        )
        self.add_output(
            "alkaline_seawater_salinity",
            val=0.0,
            shape=8760,
            units="ppt",
            desc="Salinity of the alkaline seawater",
        )
        self.add_output(
            "alkaline_seawater_temp",
            val=0.0,
            shape=8760,
            units="C",
            desc="Temperature of the alkaline seawater (°C)",
        )
        self.add_output(
            "excess_acid",
            val=0.0,
            shape=8760,
            units="m**3",
            desc="Excess acid produced (m³)",
        )

    def compute(self, inputs, outputs):
        OAE_inputs = setup_ocean_alkalinity_enhancement_inputs(self.config)

        # Call the OAE calculation method from the echem_oae module
        range_outputs, oae_outputs = echem_oae.run_ocean_alkalinity_enhancement_physics_model(
            power_profile_w=inputs["electricity_in"],
            initial_tank_volume_m3=self.config.initial_tank_volume_m3,
            oae_config=OAE_inputs,
            pump_config=echem_oae.PumpInputs(),
            seawater_config=echem_oae.SeaWaterInputs(
                sal_ppt_i=self.config.initial_salinity_ppt,
                tempC=self.config.initial_temp_C,
                dic_i=self.config.initial_dic_mol_per_L,
                pH_i=self.config.initial_pH,
            ),
            rca=echem_oae.RCALoadingCalculator(
                oae=OAE_inputs,
                seawater=echem_oae.SeaWaterInputs(
                    sal_ppt_i=self.config.initial_salinity_ppt,
                    tempC=self.config.initial_temp_C,
                    dic_i=self.config.initial_dic_mol_per_L,
                    pH_i=self.config.initial_pH,
                ),
            ),
            save_outputs=True,
            save_plots=True,
            output_dir=self.options["driver_config"]["general"]["folder_output"],
            plot_range=[3910, 4030],
        )

        outputs["co2_capture_rate_mt"] = (
            oae_outputs.OAE_outputs["mass_CO2_absorbed"] / 1000
        )  # Convert from kg to metric tons
        outputs["co2_capture_mtpy"] = oae_outputs.M_co2est
        outputs["plant_mCC_capacity_mtph"] = max(range_outputs.S1["mass_CO2_absorbed"] / 1000)
        outputs["alkaline_seawater_flow_rate"] = oae_outputs.OAE_outputs["Qout"]
        outputs["alkaline_seawater_pH"] = oae_outputs.OAE_outputs["pH_f"]
        outputs["alkaline_seawater_dic"] = oae_outputs.OAE_outputs["dic_f"]
        outputs["alkaline_seawater_ta"] = oae_outputs.OAE_outputs["ta_f"]
        outputs["alkaline_seawater_salinity"] = oae_outputs.OAE_outputs["sal_f"]
        outputs["alkaline_seawater_temp"] = oae_outputs.OAE_outputs["temp_f"]
        outputs["excess_acid"] = oae_outputs.OAE_outputs["volExcessAcid"]


@define
class OAECostModelConfig(OAEPerformanceConfig):
    """Configuration for the DOC cost model.

    Attributes:
        mass_product_tonne_yr (float): Mass of product produced per year (tonnes).
        value_product (float): Value of the product (USD/yr).
        waste_mass_tonne_yr (float): Mass of waste produced per year (tonnes).
        waste_disposal_cost (float): Cost of waste disposal (USD/yr).
        avg_base_added_seawater_mol_yr (float): Average moles of base added to seawater per year.
        base_added_seawater_max_power_mol_yr (float): Maximum power for base added
            seawater per year.
        mass_rca_g (float): Mass of RCA tumbler slurry in grams.
        acid_disposal_method (str): Method for acid disposal. Options:
            - "sell rca"
            - "sell acid"
            - "acid disposal"
    """

    mass_product_tonne_yr: float = field()


class OAECostModel(MarineCarbonCaptureCostBaseClass):
    """OpenMDAO component for computing capital (CapEx) and operational (OpEx) costs of a
        direct ocean capture (DOC) system.

    Computes:
        - CapEx (USD)
        - OpEx (USD/year)
    """

    def initialize(self):
        super().initialize()
        if echem_oae is None:
            raise ImportError(
                "The `mcm` package is required. Install it via:\n"
                "pip install git+https://github.com/NREL/MarineCarbonManagement.git"
            )

    def setup(self):
        super().setup()
        self.config = OAECostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

        self.add_input(
            "plant_mCC_capacity_mtph",
            val=0.0,
            units="t/h",
            desc="Theoretical plant maximum CO₂ capture (t/h)",
        )

    def compute(self, inputs, outputs):
        # Set up electrodialysis inputs
        setup_ocean_alkalinity_enhancement_inputs(self.config)

        # res = echem_oae.oae_cost_model(
        #     echem_mcc.ElectrodialysisCostInputs(
        #         electrodialysis_inputs=ED_inputs,
        #         mCC_yr=inputs["co2_capture_mtpy"],
        #         total_tank_volume=inputs["total_tank_volume_m3"],
        #         infrastructure_type=self.config.infrastructure_type,
        #         max_theoretical_mCC=inputs["plant_mCC_capacity_mtph"],
        #     )
        # )

        # Calculate CapEx
        outputs["CapEx"] = 10
        outputs["OpEx"] = 10
