import openmdao.api as om
import pyomo.environ as pyomo
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class PyomoRuleBaseConfig(BaseConfig):
    """
    Configuration class for the DemandOpenLoopController.

    This class defines the parameters required to configure the `DemandOpenLoopController`.

    Attributes:
        resource_name (str): Name of the resource being controlled (e.g., "hydrogen").
        resource_units (str): Units of the resource (e.g., "kg/h").
        time_steps (int): Number of time steps in the simulation.
        max_capacity (float): Maximum storage capacity of the resource (in non-rate units,
            e.g., "kg" if `resource_units` is "kg/h").
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
            as `resource_units`) or a scalar for a constant demand.
    """

    resource_name: str = field()
    # resource_rate_units: str = field()
    resource_storage_units: str = field()
    # time_steps: int = field()
    # max_capacity: float = field()
    # max_charge_percent: float = field()
    # min_charge_percent: float = field()
    # init_charge_percent: float = field()
    # max_charge_rate: float = field()
    # max_discharge_rate: float = field()
    # charge_efficiency: float = field()
    # discharge_efficiency: float = field()
    # demand_profile: int | float | list = field()
    # # added by cbay, moved here by jthomas
    # include_lifecycle_count: bool = field(default=False)


class PyomoRuleBaseClass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = PyomoRuleBaseConfig.from_dict(
            self.options["tech_config"]["model_inputs"]["dispatch_rule_parameters"]
        )

        self.add_discrete_output(
            "dispatch_block_rule_function",
            val=self.dispatch_block_rule_function,
            desc="pyomo port creation function",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """
        Return the Pyomo model elements for a given technology through the OpenMDAO
        infrastructure.

        For a template class this is not implement and raises an error.
        """

        pass

    def dispatch_block_rule_function(self, pyomo_model: pyomo.ConcreteModel, tech_name: str):
        """Initializes technology parameters, variables, constraints, and ports.
            Called during Dispatch's __init__.

        Args:
            storage: Storage instance.

        """
        # Parameters
        self._create_parameters(pyomo_model, tech_name)
        # Variables
        self._create_variables(pyomo_model, tech_name)
        # Constraints
        self._create_constraints(pyomo_model, tech_name)
        # Ports
        self._create_ports(pyomo_model, tech_name)

    def _create_parameters(self, pyomo_model, tech_name: str):
        """Create technology Pyomo parameters to add to the Pyomo model instance.

        Args:
            pyomo_model: Pyomo Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")

    def _create_variables(self, pyomo_model, tech_name: str):
        """Create technology Pyomo variables to add to the Pyomo model instance.

        Args:
            pyomo_model: Pyomo Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
        """

        raise NotImplementedError(
            "This method should be implemented in a subclass. \
                                  If no variables to add, simply use a pass function"
        )

    def _create_constraints(self, pyomo_model, tech_name: str):
        """Create technology Pyomo constraints to add to the Pyomo model instance.

        Args:
            pyomo_model: Pyomo Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
        """

        raise NotImplementedError(
            "This method should be implemented in a subclass. \
                                  If no constraints to add, simply use a pass function"
        )

    def _create_ports(self, pyomo_model, tech_name: str):
        """Create technology Pyomo port to add to the Pyomo model instance.

        Args:
            hybrid: Hybrid plant instance.

        Returns:
            Port: technology Pyomo Port object.

        """

        raise NotImplementedError("This method should be implemented in a subclass.")
