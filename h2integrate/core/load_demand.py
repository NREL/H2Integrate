import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class DemandProfileModelConfig(BaseConfig):
    """Config class for feedstock.

    Attributes:
        demand (scalar or list):  The load demand in units of `units`.
            If scalar, demand is assumed to be constant for each timestep.
            If list, then must be the the demand for each timestep.
        units (str): demand profile units (such as "galUS" or "kg")
        commodity (str, optional): name of the demanded commodity.
    """

    demand: list | int | float = field()
    units: str = field(converter=str.strip)
    commodity: str = field(converter=(str.strip, str.lower))


class DemandPerformanceModelComponent(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])

        self.config = DemandProfileModelConfig.from_dict(
            self.options["tech_config"]["model_inputs"]["performance_parameters"]
        )

        self.add_input(
            f"{self.config.commodity}_demand_profile",
            val=self.config.demand,
            shape=(n_timesteps,),
            units=f"{self.config.units}/h",  # NOTE: hardcoded to align with controllers
            desc=f"Demand profile of {self.config.commodity}",
        )

        self.add_input(
            f"{self.config.commodity}_in",
            val=0.0,
            shape=(n_timesteps,),
            units=self.config.units,
            desc=f"Amount of {self.config.commodity} demand that has already been supplied",
        )

        self.add_output(
            f"{self.config.commodity}_missed_load",
            val=self.config.demand,
            shape=(n_timesteps,),
            units=self.config.units,
            desc=f"Remaining demand profile of {self.config.commodity}",
        )

        self.add_output(
            f"{self.config.commodity}_curtailed",
            val=0.0,
            shape=(n_timesteps,),
            units=self.config.units,
            desc=f"Excess production of {self.config.commodity}",
        )

        self.add_output(
            f"{self.config.commodity}_out",
            val=0.0,
            shape=(n_timesteps,),
            units=self.config.units,
            desc=f"Production profile of {self.config.commodity}",
        )

    def compute(self, inputs, outputs):
        remaining_demand = (
            inputs[f"{self.config.commodity}_demand_profile"]
            - inputs[f"{self.config.commodity}_in"]
        )

        current_demand = np.where(remaining_demand > 0, remaining_demand, 0)
        curtailed_demand = np.where(remaining_demand < 0, -1 * remaining_demand, 0)
        outputs[f"{self.config.commodity}_missed_load"] = current_demand
        outputs[f"{self.config.commodity}_curtailed"] = curtailed_demand

        production = inputs[f"{self.config.commodity}_in"] - curtailed_demand
        outputs[f"{self.config.commodity}_out"] = production
