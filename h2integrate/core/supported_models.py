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
    ElectrolyzerFinanceModel,
    ElectrolyzerPerformanceModel,
)
from h2integrate.converters.hydrogen.dummy_electrolyzer import (
    DummyElectrolyzerCostModel,
    DummyElectrolyzerPerformanceModel,
)
from h2integrate.converters.hydrogen.eco_tools_pem_electrolyzer import (
    ECOElectrolyzerCostModel,
    ECOElectrolyzerPerformanceModel,
)
from h2integrate.converters.hydrogen.geologic.natural_geoh2_plant import (
    NaturalGeoH2CostModel,
    NaturalGeoH2FinanceModel,
    NaturalGeoH2PerformanceModel,
)
from h2integrate.converters.hydrogen.geologic.combined_geoh2_plant import (
    CombinedGeoH2CostModel,
    CombinedGeoH2FinanceModel,
    CombinedGeoH2PerformanceModel,
)
from h2integrate.converters.hydrogen.geologic.stimulated_geoh2_plant import (
    StimulatedGeoH2CostModel,
    StimulatedGeoH2FinanceModel,
    StimulatedGeoH2PerformanceModel,
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
    "pem_electrolyzer_performance": ElectrolyzerPerformanceModel,
    "pem_electrolyzer_cost": ElectrolyzerCostModel,
    "pem_electrolyzer_financial": ElectrolyzerFinanceModel,
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
    "combined_geoh2_performance": CombinedGeoH2PerformanceModel,
    "combined_geoh2_cost": CombinedGeoH2CostModel,
    "combined_geoh2_financial": CombinedGeoH2FinanceModel,
    "natural_geoh2_performance": NaturalGeoH2PerformanceModel,
    "natural_geoh2_cost": NaturalGeoH2CostModel,
    "natural_geoh2_financial": NaturalGeoH2FinanceModel,
    "stimulated_geoh2_performance": StimulatedGeoH2PerformanceModel,
    "stimulated_geoh2_cost": StimulatedGeoH2CostModel,
    "stimulated_geoh2_financial": StimulatedGeoH2FinanceModel,
    # Transport
    "cable": CablePerformanceModel,
    "pipe": PipePerformanceModel,
    "combiner_performance": CombinerPerformanceModel,
    # Storage
    "hydrogen_tank_performance": HydrogenTankPerformanceModel,
    "hydrogen_tank_cost": HydrogenTankCostModel,
}

electricity_producing_techs = ["wind", "solar", "hopp"]
