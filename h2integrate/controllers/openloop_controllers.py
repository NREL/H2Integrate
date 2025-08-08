from copy import deepcopy

import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import range_val


class ControllerBaseClass(om.ExplicitComponent):
    """
    Base class for open-loop controllers in the H2Integrate system.

    This class provides a template for implementing open-loop controllers. It defines the
    basic structure for inputs and outputs and requires subclasses to implement the `compute`
    method for specific control logic.

    Attributes:
        plant_config (dict): Configuration dictionary for the overall plant.
        tech_config (dict): Configuration dictionary for the specific technology being controlled.
    """

    def initialize(self):
        """
        Declare options for the component. See "Attributes" section in class doc strings for
        details.
        """

        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        """
        Define inputs and outputs for the component.

        This method must be implemented in subclasses to define the specific control I/O.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("This method should be implemented in a subclass.")

    def compute(self, inputs, outputs):
        """
        Perform computations for the component.

        This method must be implemented in subclasses to define the specific control logic.

        Args:
            inputs (dict): Dictionary of input values.
            outputs (dict): Dictionary of output values.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("This method should be implemented in a subclass.")


@define
class PassThroughOpenLoopControllerConfig(BaseConfig):
    resource_name: str = field()
    resource_rate_units: str = field()


class PassThroughOpenLoopController(ControllerBaseClass):
    """
    A simple pass-through controller for open-loop systems.

    This controller directly passes the input resource flow to the output without any
    modifications. It is useful for testing, as a placeholder for more complex controllers,
    and for maintaining consistency between controlled and uncontrolled frameworks as this
    'controller' does not alter the system output in any way.
    """

    def setup(self):
        self.config = PassThroughOpenLoopControllerConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        self.add_input(
            f"{self.config.resource_name}_in",
            shape_by_conn=True,
            units=self.config.resource_rate_units,
            desc=f"{self.config.resource_name} input timeseries from production to storage",
        )

        self.add_output(
            f"{self.config.resource_name}_out",
            copy_shape=f"{self.config.resource_name}_in",
            units=self.config.resource_rate_units,
            desc=f"{self.config.resource_name} output timeseries from plant after storage",
        )

    def compute(self, inputs, outputs):
        """
        Pass through input to output flows.

        Args:
            inputs (dict): Dictionary of input values.
                - {resource_name}_in: Input resource flow.
            outputs (dict): Dictionary of output values.
                - {resource_name}_out: Output resource flow, equal to the input flow.
        """

        # Assign the input to the output
        outputs[f"{self.config.resource_name}_out"] = inputs[f"{self.config.resource_name}_in"]

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
        size = self._get_var_meta(f"{self.config.resource_name}_in", "size")

        # Declare partials sparsely for all elements as an identity matrix
        # (diagonal elements are 1.0, others are 0.0)
        self.declare_partials(
            of=f"{self.config.resource_name}_out",
            wrt=f"{self.config.resource_name}_in",
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
        resource_name (str): Name of the resource being controlled (e.g., "hydrogen").
        resource_rate_units (str): Units of the resource (e.g., "kg/h").
        max_capacity (float): Maximum storage capacity of the resource (in non-rate units,
            e.g., "kg" if `resource_rate_units` is "kg/h").
        max_charge_percent (float): Maximum allowable state of charge (SOC) as a percentage
            of `max_capacity`, represented as a decimal between 0 and 1.
        min_charge_percent (float): Minimum allowable SOC as a percentage of `max_capacity`,
            represented as a decimal between 0 and 1.
        init_charge_percent (float): Initial SOC as a percentage of `max_capacity`, represented
            as a decimal between 0 and 1.
        max_charge_rate (float): Maximum rate at which the resource can be charged (in units
            per time step, e.g., "kg/time step").
        max_discharge_rate (float): Maximum rate at which the resource can be discharged (in
            units per time step, e.g., "kg/time step").
        charge_efficiency (float): Efficiency of charging the storage, represented as a decimal
            between 0 and 1 (e.g., 0.9 for 90% efficiency).
        discharge_efficiency (float): Efficiency of discharging the storage, represented as a
            decimal between 0 and 1 (e.g., 0.9 for 90% efficiency).
        demand_profile (scalar or list): The demand values for each time step (in the same units
            as `resource_rate_units`) or a scalar for a constant demand.
        n_time_steps (int): Number of time steps in the simulation. Defaults to 8760.
    """

    resource_name: str = field()
    resource_rate_units: str = field()
    max_capacity: float = field()
    max_charge_percent: float = field(validator=range_val(0, 1))
    min_charge_percent: float = field(validator=range_val(0, 1))
    init_charge_percent: float = field(validator=range_val(0, 1))
    max_charge_rate: float = field()
    max_discharge_rate: float = field()
    charge_efficiency: float = field(validator=range_val(0, 1))
    discharge_efficiency: float = field(validator=range_val(0, 1))
    demand_profile: int | float | list = field()
    n_time_steps: int = field(default=8760)


class DemandOpenLoopController(ControllerBaseClass):
    """
    A controller that manages resource flow based on demand and storage constraints.

    The `DemandOpenLoopController` computes the state of charge (SOC), output flow, curtailment,
    and missed load for a resource storage system. It uses a demand profile and storage parameters
    to determine how much of the resource to charge, discharge, or curtail at each time step.

    Note: the units of the outputs are the same as the resource units, which is typically a rate
    in H2Integrate (e.g. kg/h)

    Attributes:
        config (DemandOpenLoopControllerConfig): Configuration object containing parameters
            such as resource name, units, time steps, storage capacity, charge/discharge rates,
            efficiencies, and demand profile.

    Inputs:
        {resource_name}_in (float): Input resource flow timeseries (e.g., hydrogen production).
            - Units: Defined in `resource_rate_units` (e.g., "kg/h").

    Outputs:
        {resource_name}_out (float): Output resource flow timeseries after storage.
            - Units: Defined in `resource_rate_units` (e.g., "kg/h").
        {resource_name}_soc (float): State of charge (SOC) timeseries for the storage system.
            - Units: "unitless" (percentage of maximum capacity given as a ratio between 0 and 1).
        {resource_name}_curtailed (float): Curtailment timeseries for unused input resource.
            - Units: Defined in `resource_rate_units` (e.g., "kg/h").
            - Note: curtailment in this case does not reduce what the converter produces, but
                rather the system just does not use it (throws it away) because this controller is
                specific to the storage technology and has no influence on other technologies in
                the system.
        {resource_name}_missed_load (float): Missed load timeseries when demand exceeds supply.
            - Units: Defined in `resource_rate_units` (e.g., "kg/h").

    """

    def setup(self):
        self.config = DemandOpenLoopControllerConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        resource_name = self.config.resource_name

        self.add_input(
            f"{resource_name}_in",
            shape_by_conn=True,
            units=self.config.resource_rate_units,
            desc=f"{resource_name} input timeseries from production to storage",
        )

        if isinstance(self.config.demand_profile, int | float):
            self.config.demand_profile = [self.config.demand_profile] * self.config.n_time_steps

        self.add_input(
            f"{resource_name}_demand_profile",
            units=f"{self.config.resource_rate_units}/h",
            val=self.config.demand_profile,
            shape=self.config.n_time_steps,
            desc=f"{resource_name} demand profile timeseries",
        )

        self.add_output(
            f"{resource_name}_out",
            copy_shape=f"{resource_name}_in",
            units=self.config.resource_rate_units,
            desc=f"{resource_name} output timeseries from plant after storage",
        )

        self.add_output(
            f"{resource_name}_soc",
            copy_shape=f"{resource_name}_in",
            units="unitless",
            desc=f"{resource_name} state of charge timeseries for storage",
        )

        self.add_output(
            f"{resource_name}_curtailed",
            copy_shape=f"{resource_name}_in",
            units=self.config.resource_rate_units,
            desc=f"{resource_name} curtailment timeseries for inflow resource at \
                storage point",
        )

        self.add_output(
            f"{resource_name}_missed_load",
            copy_shape=f"{resource_name}_in",
            units=self.config.resource_rate_units,
            desc=f"{resource_name} missed load timeseries",
        )

    def compute(self, inputs, outputs):
        """
        Compute the state of charge (SOC) and output flow based on demand and storage constraints.

        """
        resource_name = self.config.resource_name
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

        demand_profile = inputs[f"{resource_name}_demand_profile"]

        # initialize outputs
        soc_array = outputs[f"{resource_name}_soc"]
        curtailment_array = outputs[f"{resource_name}_curtailed"]
        output_array = outputs[f"{resource_name}_out"]
        missed_load_array = outputs[f"{resource_name}_missed_load"]

        # Loop through each time step
        for t, demand_t in enumerate(demand_profile):
            # Get the input flow at the current time step
            input_flow = inputs[f"{resource_name}_in"][t]

            # Calculate the available charge/discharge capacity
            available_charge = (max_charge_percent - soc) * max_capacity
            available_discharge = (soc - min_charge_percent) * max_capacity

            # Initialize persistent variables for curtailment and missed load
            excess_input = 0.0
            charge = 0.0

            # Determine the output flow based on demand_t and SOC
            if demand_t > input_flow:
                # Discharge storage to meet demand
                discharge_needed = (demand_t - input_flow) / discharge_efficiency
                discharge = min(discharge_needed, available_discharge, max_discharge_rate)
                soc -= discharge / max_capacity  # soc is a ratio with value between 0 and 1
                output_array[t] = input_flow + discharge * discharge_efficiency
            else:
                # Charge storage with excess input
                excess_input = (input_flow - demand_t) * charge_efficiency
                charge = min(excess_input, available_charge, max_charge_rate)
                soc += charge / max_capacity  # soc is a ratio with value between 0 and 1
                output_array[t] = demand_t

            # Ensure SOC stays within bounds
            soc = max(min_charge_percent, min(max_charge_percent, soc))

            # Record the SOC for the current time step
            soc_array[t] = deepcopy(soc)

            # Record the curtailment at the current time step
            curtailment_array[t] = max(0, float(excess_input - charge))

            # Record the missed load the the current time step
            missed_load_array[t] = max(0, (demand_t - output_array[t]))
