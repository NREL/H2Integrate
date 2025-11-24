import numpy as np
from attrs import field, define

from h2integrate.core.validators import range_val
from h2integrate.control.control_strategies.demand_openloop_controller import (
    DemandOpenLoopControlBase,
    DemandOpenLoopControlBaseConfig,
)


@define
class FlexibleDemandOpenLoopConverterControlConfig(DemandOpenLoopControlBaseConfig):
    """Config class for flexible demand converter.

    Attributes:
        turndown_ratio (float): Minimum operating point as a fraction of ``maximum_demand``.
            Must between in range (0,1).
        ramp_down_rate_fraction (float): Ramp down rate as a fraction of ``maximum_demand``
            per timestep. Must between in range (0,1).
        ramp_up_rate_fraction (float): Ramp up rate as a fraction of ``maximum_demand``
            per timestep. Must between in range (0,1).
        min_utilization (float): Minimum total demand that must be met over the simulation
            based on ``maximum_demand``. Used to ensure that some minimum total demand is met.
            Must between in range (0,1). Utilization is calculated as:

            ``sum({commodity}_flexible_demand_profile)/sum({commodity}_demand)``
    """

    turndown_ratio: float = field(validator=range_val(0, 1.0))
    ramp_down_rate_fraction: float = field(validator=range_val(0, 1.0))
    ramp_up_rate_fraction: float = field(validator=range_val(0, 1.0))
    min_utilization: float = field(validator=range_val(0, 1.0))


class FlexibleDemandOpenLoopConverterControl(DemandOpenLoopControlBase):
    def setup(self):
        super().setup()

        n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])
        commodity = self.config.commodity_name

        self.add_input(
            "ramp_down_rate",
            val=self.config.ramp_down_rate_fraction,
            units="percent",
            desc="Maximum ramp down rate as a fraction of the maximum demand",
        )

        self.add_input(
            "ramp_up_rate",
            val=self.config.ramp_up_rate_fraction,
            units="percent",
            desc="Maximum ramp down rate as a fraction of the maximum demand",
        )

        self.add_input(
            "min_utilization",
            val=self.config.min_utilization,
            units="percent",
            desc="Minimum capacity factor based on maximum demand",
        )

        self.add_input(
            "turndown_ratio",
            val=self.config.turndown_ratio,
            units="percent",
            desc="Minimum operating point as a fraction of the maximum demand",
        )

        self.add_output(
            f"{commodity}_flexible_demand_profile",
            val=0.0,
            shape=(n_timesteps),
            units=self.config.commodity_units,
            desc=f"Flexible demand profile of {commodity}",
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
        """_summary_

        Args:
            flexible_demand_profile (_type_): _description_
            min_total_demand (_type_): _description_
            demand_bounds (_type_): _description_
            demand_threshold (_type_): _description_

        Returns:
            _type_: _description_
        """
        min_demand, rated_demand = demand_bounds
        required_extra_demand = min_total_demand - np.sum(flexible_demand_profile)

        # add extra demand to timesteps where demand is below some threshold
        i_to_increase = np.argwhere(flexible_demand_profile <= demand_threshold).flatten()
        extra_power_per_timestep = required_extra_demand / len(i_to_increase)
        flexible_demand_profile[i_to_increase] = (
            flexible_demand_profile[i_to_increase] + extra_power_per_timestep
        )
        return np.clip(flexible_demand_profile, min_demand, rated_demand)

    def make_flexible_demand(self, maximum_demand_profile, pre_demand_met, inputs):
        """Make flexible demand profile from original load met.

        Args:
            maximum_demand_profile (np.ndarray): _description_
            pre_demand_met (np.ndarray): _description_
            inputs (dict): _description_

        Returns:
            np.ndarray: _description_
        """

        # Calculate demand constraint values in units of commodity units
        rated_demand = np.max(maximum_demand_profile)
        min_demand = rated_demand * inputs["turndown_ratio"][0]  # minimum demand in commodity units
        ramp_down_rate = (
            rated_demand * inputs["ramp_down_rate"][0]
        )  # ramp down rate in commodity units
        ramp_up_rate = rated_demand * inputs["ramp_up_rate"][0]  # ramp up rate in commodity units
        min_total_demand = rated_demand * len(maximum_demand_profile) * inputs["min_utilization"][0]

        # 1) satisfy turndown constraint
        pre_demand_met_clipped = np.clip(pre_demand_met, min_demand, rated_demand)

        # 2) satisfy ramp rate constraint
        demand_bounds = (min_demand, rated_demand)
        ramp_rate_bounds = (ramp_down_rate, ramp_up_rate)
        flexible_demand_profile = self.adjust_demand_for_ramping(
            pre_demand_met_clipped, demand_bounds, ramp_rate_bounds
        )

        # 3) satisfy min utilization constraint
        if np.sum(flexible_demand_profile) < min_total_demand:
            # gradually increase power threshold in increments of 5% of rated power
            demand_threshold_percentages = np.arange(inputs["turndown_ratio"][0], 1.05, 0.05)
            for demand_threshold_percent in demand_threshold_percentages:
                demand_threshold = demand_threshold_percent * rated_demand
                # 3a) satisfy turndown constraint
                pre_demand_met_clipped = np.clip(pre_demand_met, min_demand, rated_demand)
                # 3b) adjust TODO: finish this comment
                flexible_demand_profile = (
                    self.adjust_remaining_demand_for_min_utilization_by_threshold(
                        flexible_demand_profile, min_total_demand, demand_bounds, demand_threshold
                    )
                )
                # 3c) satisfy ramp rate constraint
                flexible_demand_profile = self.adjust_demand_for_ramping(
                    flexible_demand_profile, demand_bounds, ramp_rate_bounds
                )

                if np.sum(flexible_demand_profile) >= min_total_demand:
                    break
        return flexible_demand_profile

    def compute(self, inputs, outputs):
        commodity = self.config.commodity_name
        remaining_demand = inputs[f"{commodity}_demand"] - inputs[f"{commodity}_in"]

        if self.config.min_utilization == 1.0:
            # Calculate missed load and curtailed production
            outputs[f"{commodity}_unmet_demand"] = np.where(
                remaining_demand > 0, remaining_demand, 0
            )
            outputs[f"{commodity}_unused_commodity"] = np.where(
                remaining_demand < 0, -1 * remaining_demand, 0
            )
        else:
            curtailed = np.where(remaining_demand < 0, -1 * remaining_demand, 0)
            inflexible_out = inputs[f"{commodity}_in"] - curtailed

            flexible_demand_profile = self.make_flexible_demand(
                inputs[f"{commodity}_demand"], inflexible_out, inputs
            )

            outputs[f"{commodity}_flexible_demand_profile"] = flexible_demand_profile
            flexible_remaining_demand = flexible_demand_profile - inputs[f"{commodity}_in"]

            outputs[f"{commodity}_unmet_demand"] = np.where(
                flexible_remaining_demand > 0, flexible_remaining_demand, 0
            )
            outputs[f"{commodity}_unused_commodity"] = np.where(
                flexible_remaining_demand < 0, -1 * flexible_remaining_demand, 0
            )

        # Calculate actual output based on demand met and curtailment
        outputs[f"{commodity}_out"] = (
            inputs[f"{commodity}_in"] - outputs[f"{commodity}_unused_commodity"]
        )
