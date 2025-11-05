import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs


@define
class GridBuyingPerformanceConfig(BaseConfig):
    interconnect_limit: float = field()  # kW


class GridBuyPerformanceModel(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = GridBuyingPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        # Add electricity consumed/bought
        self.add_output(
            "electricity_consumed",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Electricity consumed by the plant",
        )

        # Default the electricity demand input as the rated capacity
        self.add_input(
            "electricity_demand",
            val=self.config.interconnect_limit,
            shape=n_timesteps,
            units="kW",
            desc="Electricity demand for grid interconnect",
        )

        self.add_input(
            "interconnect_limit",
            val=self.config.interconnect_limit,
            units="kW",
            desc="Maximum power that can be bought from grid",
        )

        # Add electricity available to buy as input, default to 0 --> set using feedstock component
        self.add_input(
            "electricity_in",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Electricity available",
        )

    def compute(self, inputs, outputs):
        electricity_available = inputs["electricity_in"]

        # Amount to buy to grid (limited by interconnect and available electricity)
        # Only sell positive electricity amounts
        electricity_demand = np.where(
            inputs["electricity_demand"] > inputs["interconnect_limit"],
            inputs["interconnect_limit"],
            inputs["electricity_demand"],
        )

        outputs["electricity_consumed"] = np.minimum.reduce(
            [electricity_demand, electricity_available]
        )
