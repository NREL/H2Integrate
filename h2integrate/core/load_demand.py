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
        commodity = self.config.commodity

        self.add_input(
            f"{commodity}_demand_profile",
            val=self.config.demand,
            shape=(n_timesteps),
            units=f"{self.config.units}/h",  # NOTE: hardcoded to align with controllers
            desc=f"Demand profile of {commodity}",
        )

        self.add_input(
            f"{commodity}_in",
            val=0.0,
            shape=(n_timesteps),
            units=self.config.units,
            desc=f"Amount of {commodity} demand that has already been supplied",
        )

        self.add_output(
            f"{commodity}_missed_load",
            val=self.config.demand,
            shape=(n_timesteps),
            units=self.config.units,
            desc=f"Remaining demand profile of {commodity}",
        )

        self.add_output(
            f"{commodity}_curtailed",
            val=0.0,
            shape=(n_timesteps),
            units=self.config.units,
            desc=f"Excess production of {commodity}",
        )

        self.add_output(
            f"{commodity}_out",
            val=0.0,
            shape=(n_timesteps),
            units=self.config.units,
            desc=f"Production profile of {commodity}",
        )

    def compute(self, inputs, outputs):
        commodity = self.config.commodity
        remaining_demand = inputs[f"{commodity}_demand_profile"] - inputs[f"{commodity}_in"]

        # Calculate missed load and curtailed production
        outputs[f"{commodity}_missed_load"] = np.where(remaining_demand > 0, remaining_demand, 0)
        outputs[f"{commodity}_curtailed"] = np.where(remaining_demand < 0, -1 * remaining_demand, 0)

        # Calculate actual output based on demand met and curtailment
        outputs[f"{commodity}_out"] = inputs[f"{commodity}_in"] - outputs[f"{commodity}_curtailed"]
