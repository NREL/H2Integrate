from copy import deepcopy

import openmdao.api as om
from attrs import field, define
from numpy import ones, arange

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs


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
    resource_units: str = field()


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
            units=self.config.resource_units,
            desc=f"{self.config.resource_name} input timeseries from production to storage",
        )

        self.add_output(
            f"{self.config.resource_name}_out",
            copy_shape=f"{self.config.resource_name}_in",
            units=self.config.resource_units,
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
            rows=arange(size),
            cols=arange(size),
            val=ones(size),  # Diagonal elements are 1.0
        )


@define
class DemandOpenLoopControllerConfig(BaseConfig):
    resource_name: str = field()
    resource_units: str = field()
    time_units: str = field()
    max_charge: float = field()  # percent
    min_charge: float = field()  # percent
    init_charge: float = field()  # percent
    max_charge_rate: float = field()
    max_discharge_rate: float = field()
    charge_efficiency: float = field()
    discharge_efficiency: float = field()
    demand_profile: list = field()  # TODO does this need to be an input?


class OpenLoopController(ControllerBaseClass):
    def setup(self):
        self.config = DemandOpenLoopControllerConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        self.add_input(
            f"{self.config.resource_name}_in",
            shape_by_conn=True,
            units=self.config.resource_units,
            desc=f"{self.config.resource_name} input timeseries from production to storage",
        )

        self.add_output(
            f"{self.config.resource_name}_out",
            copy_shape=f"{self.config.resource_name}_in",
            units=self.config.resource_units,
            desc=f"{self.config.resource_name} output timeseries from plant after storage",
        )

        self.add_discrete_output(  # TODO should this be discrete or will it be included in optimization?
            f"{self.config.resource_name}_soc",
            copy_shape=f"{self.config.resource_name}_in",
            units="percent",
            desc=f"{self.config.resource_name} state of charge timeseries for storage",
        )

        self.add_discrete_output(  # TODO should this be discrete or will it be included in optimization?
            f"{self.config.resource_name}_curtailed",
            copy_shape=f"{self.config.resource_name}_in",
            units=self.config.resource_units,
            desc=f"{self.config.resource_name} curtailment timeseries for inflow resource at \
                storage point",
        )

    def compute(self, inputs, outputs, discrete_outputs):
        """
        Compute the state of charge (SOC) and output flow based on demand and storage constraints.

        """
        resource_name = self.config.resource_name
        max_charge = self.config.max_charge
        min_charge = self.config.min_charge
        init_charge = self.config.init_charge
        max_charge_rate = self.config.max_charge_rate
        max_discharge_rate = self.config.max_discharge_rate
        charge_efficiency = self.config.charge_efficiency
        discharge_efficiency = self.config.discharge_efficiency
        demand_profile = self.config.demand_profile
        # solve_approach: optimized vs heuristic
        # objective:

        # Initialize state of charge
        soc = deepcopy(init_charge)

        # Loop through each time step
        for t in range(len(demand_profile)):
            # Get the input flow and demand at the current time step
            input_flow = inputs[f"{resource_name}_in"][t]
            demand = demand_profile[t]

            # Calculate the available charge/discharge capacity
            available_charge = max_charge - soc
            available_discharge = soc - min_charge

            # Determine the output flow based on demand and SOC
            if demand > input_flow:
                # Discharge storage to meet demand
                discharge_needed = (demand - input_flow) / discharge_efficiency
                discharge = min(discharge_needed, available_discharge, max_discharge_rate)
                soc -= discharge
                outputs[f"{resource_name}_out"][t] = input_flow + discharge * discharge_efficiency
            else:
                # Charge storage with excess input
                excess_input = input_flow - demand
                charge = min(excess_input * charge_efficiency, available_charge, max_charge_rate)
                soc += charge
                outputs[f"{resource_name}_out"][t] = demand

            # Ensure SOC stays within bounds
            soc = max(min_charge, min(max_charge, soc))

            # Record the SOC for the current time step
            discrete_outputs[f"{resource_name}_soc"][t] = soc
