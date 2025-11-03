from h2integrate.resource.river import RiverResource
from h2integrate.core.feedstocks import FeedstockCostModel, FeedstockPerformanceModel
from h2integrate.transporters.pipe import PipePerformanceModel
from h2integrate.transporters.cable import CablePerformanceModel
from h2integrate.finances.profast_lco import ProFastLCO
from h2integrate.finances.profast_npv import ProFastNPV
from h2integrate.converters.steel.steel import SteelPerformanceModel, SteelCostAndFinancialModel
from h2integrate.converters.wind.wind_pysam import PYSAMWindPlantPerformanceModel
from h2integrate.finances.simple_npv_finance import NPVFinance
from h2integrate.transporters.generic_summer import GenericSummerPerformanceModel
from h2integrate.converters.hopp.hopp_wrapper import HOPPComponent
from h2integrate.converters.solar.solar_pysam import PYSAMSolarPlantPerformanceModel
from h2integrate.storage.generic_storage_cost import GenericStorageCostModel
from h2integrate.storage.hydrogen.eco_storage import H2Storage
from h2integrate.converters.wind.atb_wind_cost import ATBWindPlantCostModel
from h2integrate.storage.battery.pysam_battery import PySAMBatteryPerformanceModel
from h2integrate.transporters.generic_combiner import GenericCombinerPerformanceModel
from h2integrate.transporters.generic_splitter import GenericSplitterPerformanceModel
from h2integrate.converters.nitrogen.simple_ASU import SimpleASUCostModel, SimpleASUPerformanceModel
from h2integrate.storage.simple_generic_storage import SimpleGenericStorage
from h2integrate.storage.hydrogen.tank_baseclass import (
    HydrogenTankCostModel,
    HydrogenTankPerformanceModel,
)
from h2integrate.converters.hydrogen.wombat_model import WOMBATElectrolyzerModel
from h2integrate.storage.battery.atb_battery_cost import ATBBatteryCostModel
from h2integrate.converters.ammonia.ammonia_synloop import (
    AmmoniaSynLoopCostModel,
    AmmoniaSynLoopPerformanceModel,
)
from h2integrate.converters.water.desal.desalination import (
    ReverseOsmosisCostModel,
    ReverseOsmosisPerformanceModel,
)
from h2integrate.converters.hydrogen.basic_cost_model import BasicElectrolyzerCostModel
from h2integrate.converters.hydrogen.pem_electrolyzer import (
    ElectrolyzerCostModel,
    ElectrolyzerPerformanceModel,
)
from h2integrate.converters.solar.atb_res_com_pv_cost import ATBResComPVCostModel
from h2integrate.converters.solar.atb_utility_pv_cost import ATBUtilityPVCostModel
from h2integrate.resource.wind.nrel_developer_wtk_api import WTKNRELDeveloperAPIWindResource
from h2integrate.converters.methanol.smr_methanol_plant import (
    SMRMethanolPlantCostModel,
    SMRMethanolPlantFinanceModel,
    SMRMethanolPlantPerformanceModel,
)
from h2integrate.converters.ammonia.simple_ammonia_model import (
    SimpleAmmoniaCostModel,
    SimpleAmmoniaPerformanceModel,
)
from h2integrate.converters.methanol.co2h_methanol_plant import (
    CO2HMethanolPlantCostModel,
    CO2HMethanolPlantFinanceModel,
    CO2HMethanolPlantPerformanceModel,
)
from h2integrate.converters.natural_gas.natural_gas_cc_ct import (
    NaturalGasCostModel,
    NaturalGasPerformanceModel,
)
from h2integrate.converters.hydrogen.singlitico_cost_model import SingliticoCostModel
from h2integrate.converters.co2.marine.direct_ocean_capture import DOCCostModel, DOCPerformanceModel
from h2integrate.control.control_strategies.pyomo_controllers import (
    HeuristicLoadFollowingController,
)
from h2integrate.resource.solar.nrel_developer_goes_api_models import (
    GOESTMYSolarAPI,
    GOESConusSolarAPI,
    GOESFullDiscSolarAPI,
    GOESAggregatedSolarAPI,
)
from h2integrate.converters.hydrogen.eco_tools_pem_electrolyzer import (
    ECOElectrolyzerPerformanceModel,
)
from h2integrate.control.control_strategies.openloop_controllers import (
    DemandOpenLoopController,
    PassThroughOpenLoopController,
)
from h2integrate.converters.water_power.hydro_plant_run_of_river import (
    RunOfRiverHydroCostModel,
    RunOfRiverHydroPerformanceModel,
)
from h2integrate.converters.hydrogen.geologic.natural_geoh2_plant import (
    NaturalGeoH2CostModel,
    NaturalGeoH2FinanceModel,
    NaturalGeoH2PerformanceModel,
)
from h2integrate.control.control_rules.converters.generic_converter import (
    PyomoDispatchGenericConverter,
)
from h2integrate.converters.co2.marine.ocean_alkalinity_enhancement import (
    OAECostModel,
    OAEPerformanceModel,
    OAECostAndFinancialModel,
)
from h2integrate.converters.hydrogen.custom_electrolyzer_cost_model import (
    CustomElectrolyzerCostModel,
)
from h2integrate.converters.hydrogen.geologic.stimulated_geoh2_plant import (
    StimulatedGeoH2CostModel,
    StimulatedGeoH2FinanceModel,
    StimulatedGeoH2PerformanceModel,
)
from h2integrate.control.control_rules.storage.pyomo_storage_rule_baseclass import (
    PyomoRuleStorageBaseclass,
)


supported_models = {
    # Resources
    "river_resource": RiverResource,
    "wind_toolkit_v2_api": WTKNRELDeveloperAPIWindResource,
    "goes_aggregated_solar_v4_api": GOESAggregatedSolarAPI,
    "goes_conus_solar_v4_api": GOESConusSolarAPI,
    "goes_fulldisc_solar_v4_api": GOESFullDiscSolarAPI,
    "goes_tmy_solar_v4_api": GOESTMYSolarAPI,
    # Converters
    "atb_wind_cost": ATBWindPlantCostModel,
    "pysam_wind_plant_performance": PYSAMWindPlantPerformanceModel,
    "pysam_solar_plant_performance": PYSAMSolarPlantPerformanceModel,
    "atb_utility_pv_cost": ATBUtilityPVCostModel,
    "atb_comm_res_pv_cost": ATBResComPVCostModel,
    "run_of_river_hydro_performance": RunOfRiverHydroPerformanceModel,
    "run_of_river_hydro_cost": RunOfRiverHydroCostModel,
    "pem_electrolyzer_performance": ElectrolyzerPerformanceModel,
    "pem_electrolyzer_cost": ElectrolyzerCostModel,
    "eco_pem_electrolyzer_performance": ECOElectrolyzerPerformanceModel,
    "singlitico_electrolyzer_cost": SingliticoCostModel,
    "basic_electrolyzer_cost": BasicElectrolyzerCostModel,
    "custom_electrolyzer_cost": CustomElectrolyzerCostModel,
    "wombat": WOMBATElectrolyzerModel,
    "simple_ASU_cost": SimpleASUCostModel,
    "simple_ASU_performance": SimpleASUPerformanceModel,
    "hopp": HOPPComponent,
    "reverse_osmosis_desalination_performance": ReverseOsmosisPerformanceModel,
    "reverse_osmosis_desalination_cost": ReverseOsmosisCostModel,
    "simple_ammonia_performance": SimpleAmmoniaPerformanceModel,
    "simple_ammonia_cost": SimpleAmmoniaCostModel,
    "synloop_ammonia_performance": AmmoniaSynLoopPerformanceModel,
    "synloop_ammonia_cost": AmmoniaSynLoopCostModel,
    "steel_performance": SteelPerformanceModel,
    "steel_cost": SteelCostAndFinancialModel,
    "smr_methanol_plant_performance": SMRMethanolPlantPerformanceModel,
    "smr_methanol_plant_cost": SMRMethanolPlantCostModel,
    "smr_methanol_plant_financial": SMRMethanolPlantFinanceModel,
    "co2h_methanol_plant_performance": CO2HMethanolPlantPerformanceModel,
    "co2h_methanol_plant_cost": CO2HMethanolPlantCostModel,
    "co2h_methanol_plant_financial": CO2HMethanolPlantFinanceModel,
    "direct_ocean_capture_performance": DOCPerformanceModel,
    "direct_ocean_capture_cost": DOCCostModel,
    "ocean_alkalinity_enhancement_performance": OAEPerformanceModel,
    "ocean_alkalinity_enhancement_cost": OAECostModel,
    "ocean_alkalinity_enhancement_cost_financial": OAECostAndFinancialModel,
    "natural_geoh2_performance": NaturalGeoH2PerformanceModel,
    "natural_geoh2_cost": NaturalGeoH2CostModel,
    "natural_geoh2": NaturalGeoH2FinanceModel,
    "stimulated_geoh2_performance": StimulatedGeoH2PerformanceModel,
    "stimulated_geoh2_cost": StimulatedGeoH2CostModel,
    "stimulated_geoh2": StimulatedGeoH2FinanceModel,
    "natural_gas_performance": NaturalGasPerformanceModel,
    "natural_gas_cost": NaturalGasCostModel,
    # Transport
    "cable": CablePerformanceModel,
    "pipe": PipePerformanceModel,
    "combiner_performance": GenericCombinerPerformanceModel,
    "splitter_performance": GenericSplitterPerformanceModel,
    # Simple Summers
    "summer": GenericSummerPerformanceModel,
    # Storage
    "pysam_battery": PySAMBatteryPerformanceModel,
    "h2_storage": H2Storage,
    "hydrogen_tank_performance": HydrogenTankPerformanceModel,
    "hydrogen_tank_cost": HydrogenTankCostModel,
    "atb_battery_cost": ATBBatteryCostModel,
    "generic_storage_cost": GenericStorageCostModel,
    "simple_generic_storage": SimpleGenericStorage,
    # Control
    "pass_through_controller": PassThroughOpenLoopController,
    "demand_open_loop_controller": DemandOpenLoopController,
    "heuristic_load_following_controller": HeuristicLoadFollowingController,
    # Dispatch
    "pyomo_dispatch_generic_converter": PyomoDispatchGenericConverter,
    "pyomo_dispatch_generic_storage": PyomoRuleStorageBaseclass,
    # Feedstock
    "feedstock_performance": FeedstockPerformanceModel,
    "feedstock_cost": FeedstockCostModel,
    # Finance
    "ProFastComp": ProFastLCO,
    "ProFastNPV": ProFastNPV,
    "NPVFinance": NPVFinance,
}

electricity_producing_techs = ["wind", "solar", "pv", "river", "hopp", "natural_gas_plant"]
