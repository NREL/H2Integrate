import openmdao.api as om
import pyomo.environ as pyomo


class PyomoRuleBaseClass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
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

    def dispatch_block_rule_function(self, pyomo_model: pyomo.ConcreteModel):
        """Initializes technology parameters, variables, constraints, and ports.
            Called during Dispatch's __init__.

        Args:
            storage: Storage instance.

        """
        # Parameters
        self._create_parameters(pyomo_model)
        # Variables
        self._create_variables(pyomo_model)
        # Constraints
        self._create_constraints(pyomo_model)
        # Ports
        self._create_ports(pyomo_model)

    def _create_parameters(self, pyomo_model):
        """Create technology Pyomo parameters to add to the Pyomo model instance.

        Args:
            pyomo_model: Pyomo Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")

    def _create_variables(self, pyomo_model):
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

    def _create_constraints(self, pyomo_model):
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

    def _create_ports(self, hybrid):
        """Create technology Pyomo port to add to the Pyomo model instance.

        Args:
            hybrid: Hybrid plant instance.

        Returns:
            Port: technology Pyomo Port object.

        """

        raise NotImplementedError("This method should be implemented in a subclass.")
