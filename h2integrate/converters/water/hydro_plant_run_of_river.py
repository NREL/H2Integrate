import numpy as np
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.converters.water.hydro_plant_baseclass import (
    HydroCostBaseClass,
    HydroPerformanceBaseClass,
)


@define
class RunOfRiverHydroPerformanceConfig(BaseConfig):
    """Configuration class for the HydroPlantPerformanceComponent.
    This class defines the parameters for the hydro plant performance model.

    Args:
        plant_capacity_mw (float): Capacity of the hydro plant in MW.
        water_density (float): Density of water in kg/m^3.
        acceleration_gravity (float): Acceleration due to gravity in m/s^2.
        turbine_efficiency (float): Efficiency of the turbine as a decimal.
        head (float): Head of the water in meters.
        flow_rate (list): Flow rate of water in m^3/s.
    """

    plant_capacity_mw: float = field()
    water_density: float = field()
    acceleration_gravity: float = field()
    turbine_efficiency: float = field()
    head: float = field()
    flow_rate: list = field()


class RunOfRiverHydroPerformanceModel(HydroPerformanceBaseClass):
    """
    An OpenMDAO component for modeling the performance of a hydro plant.
    Computes annual electricity production based on water flow rate and turbine efficiency.
    """

    def initialize(self):
        super().initialize()

    def setup(self):
        super().setup()
        self.config = RunOfRiverHydroPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

    def compute(self, inputs, outputs):
        # Calculate the power output of the hydro plant
        power_output = (
            self.config.water_density
            * self.config.acceleration_gravity
            * self.config.turbine_efficiency
            * self.config.head
            * self.config.flow_rate
        ) / 1e3  # Convert to kW

        # power_output can't be greater than plant_capacity_mw
        plant_capacity_kw = self.config.plant_capacity_mw * 1e3
        power_output = np.clip(power_output, 0, plant_capacity_kw)

        # Distribute the power output over the number of time steps
        outputs["electricity"] = power_output


@define
class RunOfRiverHydroCostConfig(BaseConfig):
    """Configuration class for the HydroPlantCostComponent.
    This class defines the parameters for the hydro plant cost model.

    Args:
        plant_capacity_mw (float): Capacity of the hydro plant in MW.
        capital_cost (float): Capital cost of the hydro plant in USD/kW.
        operational_cost (float): Operational cost of the hydro plant in USD/year.
    """

    plant_capacity_mw: float = field()
    capital_cost: float = field()
    operational_cost: float = field()


class RunOfRiverHydroCostModel(HydroCostBaseClass):
    """
    An OpenMDAO component that calculates the capital expenditure (CapEx) for a hydro plant.

    Just a placeholder for now, but can be extended with more detailed cost models.
    """

    def initialize(self):
        super().initialize()

    def setup(self):
        super().setup()
        self.config = RunOfRiverHydroCostConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

    def compute(self, inputs, outputs):
        capex_kw = self.config.capital_cost
        opex_kw = self.config.operational_cost
        total_capacity_kw = self.config.plant_capacity_mw * 1e3

        outputs["CapEx"] = capex_kw * total_capacity_kw
        outputs["OpEx"] = opex_kw * total_capacity_kw
