import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class DemandOpenLoopControlBaseConfig(BaseConfig):
    """Config class for defining a demand profile.

    Attributes:
        commodity_name (str): Name of the commodity being controlled (e.g., "hydrogen").
        commodity_units (str): Units of the commodity (e.g., "kg/h").
        demand_profile (scalar or list): The demand values for each time step (in the same units
            as `commodity_units`) or a scalar for a constant demand.
    """

    commodity_units: str = field(converter=str.strip)
    commodity_name: str = field(converter=(str.strip, str.lower))
    demand_profile: int | float | list = field()


class DemandOpenLoopControlBase(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])

        # self.config = DemandOpenLoopControlBaseConfig.from_dict(
        #     self.options["tech_config"]["model_inputs"]["control_parameters"]
        # )
        commodity = self.config.commodity_name

        self.add_input(
            f"{commodity}_demand",
            val=self.config.demand_profile,
            shape=(n_timesteps),
            units=self.config.commodity_units,  # NOTE: hardcoded to align with controllers
            desc=f"Demand profile of {commodity}",
        )

        self.add_input(
            f"{commodity}_in",
            val=0.0,
            shape=(n_timesteps),
            units=self.config.commodity_units,
            desc=f"Amount of {commodity} demand that has already been supplied",
        )

        self.add_output(
            f"{commodity}_unmet_demand",
            val=self.config.demand_profile,
            shape=(n_timesteps),
            units=self.config.commodity_units,
            desc=f"Remaining demand profile of {commodity}",
        )

        self.add_output(
            f"{commodity}_unused_commodity",
            val=0.0,
            shape=(n_timesteps),
            units=self.config.commodity_units,
            desc=f"Excess production of {commodity}",
        )

        self.add_output(
            f"{commodity}_out",
            val=0.0,
            shape=(n_timesteps),
            units=self.config.commodity_units,
            desc=f"Production profile of {commodity}",
        )

        self.add_output(
            f"total_{commodity}_unmet_demand",
            units=self.config.commodity_units,
            desc="Total unmet demand",
        )

    def compute():
        raise NotImplementedError("This method should be implemented in a subclass.")
