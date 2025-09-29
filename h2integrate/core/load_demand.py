import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig
from h2integrate.core.validators import range_val


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


@define
class FlexibleDemandProfileModelConfig(BaseConfig):
    """Config class for feedstock.

    Attributes:
        demand (scalar or list):  The load demand in units of `units`.
            If scalar, demand is assumed to be constant for each timestep.
            If list, then must be the the demand for each timestep.
        units (str): demand profile units (such as "galUS" or "kg")
        commodity (str, optional): name of the demanded commodity.
    """

    maximum_demand: list | int | float = field()
    units: str = field(converter=str.strip)
    commodity: str = field(converter=(str.strip, str.lower))
    turndown_ratio: float = field(validator=range_val(0, 1.0))
    ramp_down_rate_fraction: float = field(validator=range_val(0, 1.0))
    ramp_up_rate_fraction: float = field(validator=range_val(0, 1.0))
    min_utilization: float = field(validator=range_val(0, 1.0))


class FlexibleDemandPerformanceModelComponent(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])

        self.config = FlexibleDemandProfileModelConfig.from_dict(
            self.options["tech_config"]["model_inputs"]["performance_parameters"]
        )
        commodity = self.config.commodity

        self.add_input(
            f"{commodity}_demand_profile",
            val=self.config.maximum_demand,
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

    def adjust_demand_for_ramping(self, pre_demand_met_clipped, demand_bounds, ramp_rate_bounds):
        min_demand, rated_demand = demand_bounds
        ramp_down_rate, ramp_up_rate = ramp_rate_bounds

        # Instantiate the flexible demand profile array and populate the first timestep
        # with the first value from pre_demand_met_clipped
        flexible_demand_profile = np.zeros(len(pre_demand_met_clipped))
        flexible_demand_profile[0] = pre_demand_met_clipped[0]

        # Loop through each timestep and adjust for ramping constraints
        for i in range(1, len(flexible_demand_profile)):
            prior_timestep_demand = flexible_demand_profile[i - 1]

            # Calculate the change in load from the prior timestep
            load_change = pre_demand_met_clipped[i] - prior_timestep_demand

            # If ramp is too steep down, set new_demand accordingly
            if load_change < (-1 * ramp_down_rate):
                new_demand = prior_timestep_demand - ramp_down_rate
                flexible_demand_profile[i] = np.clip(new_demand, min_demand, rated_demand)

            # If ramp is too steep up, set new_demand accordingly
            elif load_change > ramp_up_rate:
                new_demand = prior_timestep_demand + ramp_up_rate
                flexible_demand_profile[i] = np.clip(new_demand, min_demand, rated_demand)

            else:
                flexible_demand_profile[i] = pre_demand_met_clipped[i]

        return flexible_demand_profile

    def adjust_remaining_demand_for_min_utilization_by_threshold(
        self, flexible_demand_profile, min_total_demand, demand_bounds, demand_threshold
    ):
        min_demand, rated_demand = demand_bounds
        required_extra_demand = min_total_demand - np.sum(flexible_demand_profile)
        # add extra demand to timesteps where demand is below some threshold
        i_to_increase = np.argwhere(flexible_demand_profile <= demand_threshold).flatten()
        extra_power_per_timestep = required_extra_demand / len(i_to_increase)
        flexible_demand_profile[i_to_increase] = (
            flexible_demand_profile[i_to_increase] + extra_power_per_timestep
        )
        return np.clip(flexible_demand_profile, min_demand, rated_demand)

    def make_flexible_demand(self, maximum_demand_profile, pre_demand_met):
        rated_demand = np.max(maximum_demand_profile)
        min_demand = rated_demand * self.config.turndown_ratio
        ramp_down_rate = rated_demand * self.config.ramp_down_rate_fraction
        ramp_up_rate = rated_demand * self.config.ramp_up_rate_fraction
        min_total_demand = rated_demand * len(maximum_demand_profile) * self.config.min_utilization

        demand_bounds = (min_demand, rated_demand)
        ramp_rate_bounds = (ramp_down_rate, ramp_up_rate)
        # make flexible demand from original load met

        # 1) satisfy turndown constraint
        pre_demand_met_clipped = np.clip(pre_demand_met, min_demand, rated_demand)
        # 2) satisfy ramp rate constraint
        flexible_demand_profile = self.adjust_demand_for_ramping(
            pre_demand_met_clipped, demand_bounds, ramp_rate_bounds
        )

        # 3) satisfy min utilization constraint
        if np.sum(flexible_demand_profile) < min_total_demand:
            # gradually increase power threshold in increments of 5% of rated power
            demand_threshold_percentages = np.arange(self.config.turndown_ratio, 1.05, 0.05)
            for demand_threshold_percent in demand_threshold_percentages:
                demand_threshold = demand_threshold_percent * rated_demand
                # 1) satisfy turndown constraint
                pre_demand_met_clipped = np.clip(pre_demand_met, min_demand, rated_demand)
                # 2) satisfy ramp rate constraint
                flexible_demand_profile = (
                    self.adjust_remaining_demand_for_min_utilization_by_threshold(
                        flexible_demand_profile, min_total_demand, demand_bounds, demand_threshold
                    )
                )
                flexible_demand_profile = self.adjust_demand_for_ramping(
                    flexible_demand_profile, demand_bounds, ramp_rate_bounds
                )

                if np.sum(flexible_demand_profile) >= min_total_demand:
                    break
        return flexible_demand_profile

    def compute(self, inputs, outputs):
        commodity = self.config.commodity
        remaining_demand = inputs[f"{commodity}_demand_profile"] - inputs[f"{commodity}_in"]

        if self.config.min_utilization == 1.0:
            # Calculate missed load and curtailed production
            outputs[f"{commodity}_missed_load"] = np.where(
                remaining_demand > 0, remaining_demand, 0
            )
            outputs[f"{commodity}_curtailed"] = np.where(
                remaining_demand < 0, -1 * remaining_demand, 0
            )
        else:
            curtailed = np.where(remaining_demand < 0, -1 * remaining_demand, 0)
            inflexible_out = inputs[f"{commodity}_in"] - curtailed

            flexible_demand_profile = self.make_flexible_demand(
                inputs[f"{commodity}_demand_profile"], inflexible_out
            )
            flexible_remaining_demand = flexible_demand_profile - inputs[f"{commodity}_in"]

            outputs[f"{commodity}_missed_load"] = np.where(
                flexible_remaining_demand > 0, flexible_remaining_demand, 0
            )
            outputs[f"{commodity}_curtailed"] = np.where(
                flexible_remaining_demand < 0, -1 * flexible_remaining_demand, 0
            )

        # Calculate actual output based on demand met and curtailment
        outputs[f"{commodity}_out"] = inputs[f"{commodity}_in"] - outputs[f"{commodity}_curtailed"]
