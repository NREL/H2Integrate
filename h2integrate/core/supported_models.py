from h2integrate.transporters.pipe import PipePerformanceModel
from h2integrate.transporters.cable import CablePerformanceModel
from h2integrate.converters.steel.steel import SteelPerformanceModel, SteelCostAndFinancialModel
from h2integrate.converters.wind.wind_plant import WindPlantCostModel, WindPlantPerformanceModel
from h2integrate.transporters.power_combiner import CombinerPerformanceModel
from h2integrate.converters.hopp.hopp_wrapper import HOPPComponent
from h2integrate.converters.solar.solar_pysam import PYSAMSolarPlantPerformanceModel
from h2integrate.storage.hydrogen.eco_storage import H2Storage
from h2integrate.storage.hydrogen.tank_baseclass import (
    HydrogenTankCostModel,
    HydrogenTankPerformanceModel,
)
from h2integrate.converters.wind.wind_plant_pysam import PYSAMWindPlantPerformanceModel
from h2integrate.converters.wind.dummy_wind_turbine import DummyPlantCost, DummyPlantPerformance
from h2integrate.converters.ammonia.ammonia_baseclass import (
    AmmoniaCostModel,
    AmmoniaPerformanceModel,
)
from h2integrate.converters.desalination.desalination import (
    ReverseOsmosisCostModel,
    ReverseOsmosisPerformanceModel,
)
from h2integrate.converters.hydrogen.pem_electrolyzer import (
    ElectrolyzerCostModel,
    ElectrolyzerPerformanceModel,
)
from h2integrate.converters.hydrogen.dummy_electrolyzer import (
    DummyElectrolyzerCostModel,
    DummyElectrolyzerPerformanceModel,
)
from h2integrate.converters.methanol.smr_methanol_plant import (
    SMRMethanolPlantCostModel,
    SMRMethanolPlantFinanceModel,
    SMRMethanolPlantPerformanceModel,
)
from h2integrate.converters.water.hydro_plant_run_of_river import (
    RunOfRiverHydroCostModel,
    RunOfRiverHydroPerformanceModel,
)
from h2integrate.converters.hydrogen.eco_tools_pem_electrolyzer import (
    ECOElectrolyzerCostModel,
    ECOElectrolyzerPerformanceModel,
)


supported_models = {
    # Converters
    "dummy_wind_turbine_performance": DummyPlantPerformance,
    "dummy_wind_turbine_cost": DummyPlantCost,
    "dummy_electrolyzer_performance": DummyElectrolyzerPerformanceModel,
    "dummy_electrolyzer_cost": DummyElectrolyzerCostModel,
    "wind_plant_performance": WindPlantPerformanceModel,
    "wind_plant_cost": WindPlantCostModel,
    "pysam_wind_plant_performance": PYSAMWindPlantPerformanceModel,
    "pysam_solar_plant_performance": PYSAMSolarPlantPerformanceModel,
    "run_of_river_hydro_performance": RunOfRiverHydroPerformanceModel,
    "run_of_river_hydro_cost": RunOfRiverHydroCostModel,
    "pem_electrolyzer_performance": ElectrolyzerPerformanceModel,
    "pem_electrolyzer_cost": ElectrolyzerCostModel,
    "eco_pem_electrolyzer_performance": ECOElectrolyzerPerformanceModel,
    "eco_pem_electrolyzer_cost": ECOElectrolyzerCostModel,
    "h2_storage": H2Storage,
    "hopp": HOPPComponent,
    "reverse_osmosis_desalination_performance": ReverseOsmosisPerformanceModel,
    "reverse_osmosis_desalination_cost": ReverseOsmosisCostModel,
    "ammonia_performance": AmmoniaPerformanceModel,
    "ammonia_cost": AmmoniaCostModel,
    "steel_performance": SteelPerformanceModel,
    "steel_cost": SteelCostAndFinancialModel,
    "smr_methanol_plant_performance": SMRMethanolPlantPerformanceModel,
    "smr_methanol_plant_cost": SMRMethanolPlantCostModel,
    "methanol_plant_financial": SMRMethanolPlantFinanceModel,
    # Transport
    "cable": CablePerformanceModel,
    "pipe": PipePerformanceModel,
    "combiner_performance": CombinerPerformanceModel,
    # Storage
    "hydrogen_tank_performance": HydrogenTankPerformanceModel,
    "hydrogen_tank_cost": HydrogenTankCostModel,
}

electricity_producing_techs = ["wind", "solar", "run_of_river_hydro", "hopp"]
