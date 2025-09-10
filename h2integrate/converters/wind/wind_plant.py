from attrs import field, define
from hopp.simulation.technologies.sites import SiteInfo, flatirons_site
from hopp.simulation.technologies.wind.wind_plant import WindPlant

from h2integrate.core.utilities import BaseConfig, CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.model_baseclasses import CostModelBaseClass
from h2integrate.converters.wind.wind_plant_baseclass import WindPerformanceBaseClass


@define
class WindPlantPerformanceModelConfig(BaseConfig):
    num_turbines: int = field()
    turbine_rating_kw: float = field()
    rotor_diameter: float = field()
    hub_height: float = field()
    layout_mode: str = field()
    model_name: str = field()
    model_input_file: str = field()
    layout_params: dict = field()
    rating_range_kw: list = field()
    floris_config: str = field()
    operational_losses: float = field()
    timestep: list = field()
    fin_model: list = field()
    name: str = field()
    turbine_name: str = field()
    turbine_group: str = field()
    override_wind_resource_height: bool = field()
    adjust_air_density_for_elevation: bool = field()


@define
class WindPlantPerformanceModelPlantConfig(BaseConfig):
    plant_life: int = field()


class WindPlantPerformanceModel(WindPerformanceBaseClass):
    """
    An OpenMDAO component that wraps a WindPlant model.
    It takes wind parameters as input and outputs power generation data.
    """

    def setup(self):
        super().setup()
        self.config = WindPlantPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        self.plant_config = WindPlantPerformanceModelPlantConfig.from_dict(
            self.options["plant_config"]["plant"], strict=False
        )
        self.site = SiteInfo(flatirons_site)
        self.wind_plant = WindPlant(self.site, self.config)

    def compute(self, inputs, outputs):
        # Assumes the WindPlant instance has a method to simulate and return power output
        self.wind_plant.simulate_power(self.plant_config.plant_life)
        outputs["electricity_out"] = self.wind_plant._system_model.value("gen")


@define
class WindPlantCostModelConfig(CostModelBaseConfig):
    num_turbines: int = field()
    turbine_rating_kw: float = field()
    cost_per_kw: float = field()


class WindPlantCostModel(CostModelBaseClass):
    """
    An OpenMDAO component that calculates the capital expenditure (CapEx) for a wind plant.

    Just a placeholder for now, but can be extended with more detailed cost models.
    """

    def setup(self):
        self.config = WindPlantCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        num_turbines = self.config.num_turbines
        turbine_rating_kw = self.config.turbine_rating_kw
        cost_per_kw = self.config.cost_per_kw

        # Calculate CapEx
        total_capacity_kw = num_turbines * turbine_rating_kw
        outputs["CapEx"] = total_capacity_kw * cost_per_kw
        outputs["OpEx"] = 0.03 * total_capacity_kw * cost_per_kw  # placeholder scalar value
