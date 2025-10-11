from copy import deepcopy

import numpy as np
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import range_val, range_val_or_none
from h2integrate.control.control_strategies.controller_baseclass import ControllerBaseClass


@define
class PassThroughOpenLoopControllerConfig(BaseConfig):
    commodity_name: str = field()
    commodity_units: str = field()


class PassThroughOpenLoopController(ControllerBaseClass):
    """
    A simple pass-through controller for open-loop systems.

    This controller directly passes the input commodity flow to the output without any
    modifications. It is useful for testing, as a placeholder for more complex controllers,
    and for maintaining consistency between controlled and uncontrolled frameworks as this
    'controller' does not alter the system output in any way.
    """

    def setup(self):
        self.config = PassThroughOpenLoopControllerConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        self.add_input(
            f"{self.config.commodity_name}_in",
            shape_by_conn=True,
            units=self.config.commodity_units,
            desc=f"{self.config.commodity_name} input timeseries from production to storage",
        )

        self.add_output(
            f"{self.config.commodity_name}_out",
            copy_shape=f"{self.config.commodity_name}_in",
            units=self.config.commodity_units,
            desc=f"{self.config.commodity_name} output timeseries from plant after storage",
        )

    def compute(self, inputs, outputs):
        """
        Pass through input to output flows.

        Args:
            inputs (dict): Dictionary of input values.
                - {commodity_name}_in: Input commodity flow.
            outputs (dict): Dictionary of output values.
                - {commodity_name}_out: Output commodity flow, equal to the input flow.
        """

        # Assign the input to the output
        outputs[f"{self.config.commodity_name}_out"] = inputs[f"{self.config.commodity_name}_in"]

    def setup_partials(self):
        """
        Declare partial derivatives as unity throughout the design space.

        This method specifies that the derivative of the output with respect to the input is
        always 1.0, consistent with the pass-through behavior.

        Note:
        This method is not currently used and isn't strictly needed if you're creating other
        controllers; it is included as a nod towards potential future development enabling
        more derivative information passing.
        """

        # Get the size of the input/output array
        size = self._get_var_meta(f"{self.config.commodity_name}_in", "size")

        # Declare partials sparsely for all elements as an identity matrix
        # (diagonal elements are 1.0, others are 0.0)
        self.declare_partials(
            of=f"{self.config.commodity_name}_out",
            wrt=f"{self.config.commodity_name}_in",
            rows=np.arange(size),
            cols=np.arange(size),
            val=np.ones(size),  # Diagonal elements are 1.0
        )


@define
class DemandOpenLoopControllerConfig(BaseConfig):
    """
    Configuration class for the DemandOpenLoopController.

    This class defines the parameters required to configure the `DemandOpenLoopController`.

    Attributes:
        commodity_name (str): Name of the commodity being controlled (e.g., "hydrogen").
        commodity_units (str): Units of the commodity (e.g., "kg").
        max_capacity (float): Maximum storage capacity of the commodity (in non-rate units,
            e.g., "kg" if `commodity_units` is "kg").
        max_charge_percent (float): Maximum allowable state of charge (SOC) as a percentage
            of `max_capacity`, represented as a decimal between 0 and 1.
        min_charge_percent (float): Minimum allowable SOC as a percentage of `max_capacity`,
            represented as a decimal between 0 and 1.
        init_charge_percent (float): Initial SOC as a percentage of `max_capacity`, represented
            as a decimal between 0 and 1.
        max_charge_rate (float): Maximum rate at which the commodity can be charged (in units
            per time step, e.g., "kg/time step"). This rate does not include the charge_efficiency.
        max_discharge_rate (float): Maximum rate at which the commodity can be discharged (in
            units per time step, e.g., "kg/time step"). This rate does not include the
            discharge_efficiency.
        charge_efficiency (float | None): Efficiency of charging the storage, represented as a
            decimal between 0 and 1 (e.g., 0.9 for 90% efficiency). Optional if
            `round_trip_efficiency` is provided.
        discharge_efficiency (float | None): Efficiency of discharging the storage, represented
            as a decimal between 0 and 1 (e.g., 0.9 for 90% efficiency). Optional if
            `round_trip_efficiency` is provided.
        round_trip_efficiency (float | None): Combined efficiency of charging and discharging
            the storage, represented as a decimal between 0 and 1 (e.g., 0.81 for 81% efficiency).
            Optional if `charge_efficiency` and `discharge_efficiency` are provided.
        demand_profile (scalar or list): The demand values for each time step (in the same units
            as `commodity_units`) or a scalar for a constant demand.
    """

    commodity_name: str = field()
    commodity_units: str = field()
    max_capacity: float = field()
    max_charge_percent: float = field(validator=range_val(0, 1))
    min_charge_percent: float = field(validator=range_val(0, 1))
    init_charge_percent: float = field(validator=range_val(0, 1))
    max_charge_rate: float = field()
    max_discharge_rate: float = field()
    demand_profile: int | float | list = field()
    charge_efficiency: float | None = field(default=None, validator=range_val_or_none(0, 1))
    discharge_efficiency: float | None = field(default=None, validator=range_val_or_none(0, 1))
    round_trip_efficiency: float | None = field(default=None, validator=range_val_or_none(0, 1))

    def __attrs_post_init__(self):
        """
        Post-initialization logic to validate and calculate efficiencies.

        Ensures that either `charge_efficiency` and `discharge_efficiency` are provided,
        or `round_trip_efficiency` is provided. If `round_trip_efficiency` is provided,
        it calculates `charge_efficiency` and `discharge_efficiency` as the square root
        of `round_trip_efficiency`.
        """
        if self.round_trip_efficiency is not None:
            if self.charge_efficiency is not None or self.discharge_efficiency is not None:
                raise ValueError(
                    "Provide either `round_trip_efficiency` or both `charge_efficiency` "
                    "and `discharge_efficiency`, but not both."
                )
            # Calculate charge and discharge efficiencies from round-trip efficiency
            self.charge_efficiency = np.sqrt(self.round_trip_efficiency)
            self.discharge_efficiency = np.sqrt(self.round_trip_efficiency)
        elif self.charge_efficiency is not None and self.discharge_efficiency is not None:
            # Ensure both charge and discharge efficiencies are provided
            pass
        else:
            raise ValueError(
                "You must provide either `round_trip_efficiency` or both "
                "`charge_efficiency` and `discharge_efficiency`."
            )


class DemandOpenLoopController(ControllerBaseClass):
    """
    A controller that manages commodity flow based on demand and storage constraints.

    The `DemandOpenLoopController` computes the state of charge (SOC), output flow, curtailment,
    and missed load for a commodity storage system. It uses a demand profile and storage parameters
    to determine how much of the commodity to charge, discharge, or curtail at each time step.

    Note: the units of the outputs are the same as the commodity units, which is typically a rate
    in H2Integrate (e.g. kg/h)

    Attributes:
        config (DemandOpenLoopControllerConfig): Configuration object containing parameters
            such as commodity name, units, time steps, storage capacity, charge/discharge rates,
            efficiencies, and demand profile.

    Inputs:
        {commodity_name}_in (float): Input commodity flow timeseries (e.g., hydrogen production).
            - Units: Defined in `commodity_units` (e.g., "kg").

    Outputs:
        {commodity_name}_out (float): Output commodity flow timeseries after storage.
            - Units: Defined in `commodity_rate` (e.g., "kg").
        {commodity_name}_soc (float): State of charge (SOC) timeseries for the storage system.
            - Units: "unitless" (percentage of maximum capacity given as a ratio between 0 and 1).
        {commodity_name}_unused_commodity (float): Curtailment timeseries for unused
        input commodity.
            - Units: Defined in `commodity_units` (e.g., "kg").
            - Note: curtailment in this case does not reduce what the converter produces, but
                rather the system just does not use it (throws it away) because this controller is
                specific to the storage technology and has no influence on other technologies in
                the system.
        {commodity_name}_unmet_demand (float): Missed load timeseries when demand exceeds supply.
            - Units: Defined in `commodity_units` (e.g., "kg").

    """

    def setup(self):
        self.config = DemandOpenLoopControllerConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        self.n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        commodity_name = self.config.commodity_name

        self.add_input(
            f"{commodity_name}_in",
            shape_by_conn=True,
            units=f"{self.config.commodity_units}",
            desc=f"{commodity_name} input timeseries from production to storage",
        )

        if isinstance(self.config.demand_profile, int | float):
            self.config.demand_profile = [self.config.demand_profile] * self.n_timesteps

        self.add_input(
            f"{commodity_name}_demand_profile",
            units=f"{self.config.commodity_units}",
            val=self.config.demand_profile,
            shape=self.n_timesteps,
            desc=f"{commodity_name} demand profile timeseries",
        )

        self.add_output(
            f"{commodity_name}_out",
            copy_shape=f"{commodity_name}_in",
            units=f"{self.config.commodity_units}",
            desc=f"{commodity_name} output timeseries from plant after storage",
        )

        self.add_output(
            f"{commodity_name}_soc",
            copy_shape=f"{commodity_name}_in",
            units="unitless",
            desc=f"{commodity_name} state of charge timeseries for storage",
        )

        self.add_output(
            f"{commodity_name}_unused_commodity",
            copy_shape=f"{commodity_name}_in",
            units=self.config.commodity_units,
            desc=f"{commodity_name} curtailment timeseries for inflow commodity at \
                storage point",
        )

        self.add_output(
            f"{commodity_name}_unmet_demand",
            copy_shape=f"{commodity_name}_in",
            units=self.config.commodity_units,
            desc=f"{commodity_name} missed load timeseries",
        )

    def compute(self, inputs, outputs):
        """
        Compute the state of charge (SOC) and output flow based on demand and storage constraints.

        """
        commodity_name = self.config.commodity_name
        max_capacity = self.config.max_capacity
        max_charge_percent = self.config.max_charge_percent
        min_charge_percent = self.config.min_charge_percent
        init_charge_percent = self.config.init_charge_percent
        max_charge_rate = self.config.max_charge_rate
        max_discharge_rate = self.config.max_discharge_rate
        charge_efficiency = self.config.charge_efficiency
        discharge_efficiency = self.config.discharge_efficiency

        # Initialize time-step state of charge prior to loop so the loop starts with
        # the previous time step's value
        soc = deepcopy(init_charge_percent)

        demand_profile = inputs[f"{commodity_name}_demand_profile"]

        # initialize outputs
        soc_array = outputs[f"{commodity_name}_soc"]
        unused_commodity_array = outputs[f"{commodity_name}_unused_commodity"]
        output_array = outputs[f"{commodity_name}_out"]
        unmet_demand_array = outputs[f"{commodity_name}_unmet_demand"]

        # Loop through each time step
        for t, demand_t in enumerate(demand_profile):
            # Get the input flow at the current time step
            input_flow = inputs[f"{commodity_name}_in"][t]

            # Calculate the available charge/discharge capacity
            available_charge = (max_charge_percent - soc) * max_capacity
            available_discharge = (soc - min_charge_percent) * max_capacity

            # Initialize persistent variables for curtailment and missed load
            unused_input = 0.0
            charge = 0.0

            # Determine the output flow based on demand_t and SOC
            if demand_t > input_flow:
                # Discharge storage to meet demand.
                # `discharge_needed` is as seen by the storage
                discharge_needed = (demand_t - input_flow) / discharge_efficiency
                # `discharge` is as seen by the storage, but `max_discharge_rate` is as observed
                # outside the storage
                discharge = min(
                    discharge_needed, available_discharge, max_discharge_rate / discharge_efficiency
                )
                soc -= discharge / max_capacity  # soc is a ratio with value between 0 and 1
                # output is as observed outside the storage, so we need to adjust `discharge` by
                # applying `discharge_efficiency`.
                output_array[t] = input_flow + discharge * discharge_efficiency
            else:
                # Charge storage with unused input
                # `unused_input` is as seen outside the storage
                unused_input = input_flow - demand_t
                # `charge` is as seen by the storage, but the things being compared should all be as
                # seen outside the storage so we need to adjust `available_charge` outside the
                # storage view and the final result back into the storage view.
                charge = (
                    min(unused_input, available_charge / charge_efficiency, max_charge_rate)
                    * charge_efficiency
                )
                soc += charge / max_capacity  # soc is a ratio with value between 0 and 1
                output_array[t] = demand_t

            # Ensure SOC stays within bounds
            soc = max(min_charge_percent, min(max_charge_percent, soc))

            # Record the SOC for the current time step
            soc_array[t] = deepcopy(soc)

            # Record the curtailment at the current time step. Adjust `charge` from storage view to
            # outside view for curtailment
            unused_commodity_array[t] = max(0, float(unused_input - charge / charge_efficiency))

            # Record the missed load at the current time step
            unmet_demand_array[t] = max(0, (demand_t - output_array[t]))

        outputs[f"{commodity_name}_out"] = output_array

        # Return the SOC
        outputs[f"{commodity_name}_soc"] = soc_array

        # Return the unused commodity
        outputs[f"{commodity_name}_unused_commodity"] = unused_commodity_array

        # Return the unmet load demand
        outputs[f"{commodity_name}_unmet_demand"] = unmet_demand_array
