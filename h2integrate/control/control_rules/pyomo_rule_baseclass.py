import openmdao.api as om
import pyomo.environ as pyo
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class PyomoRuleBaseConfig(BaseConfig):
    """
    Configuration class for the PyomoRuleBaseConfig.

    This class defines the parameters required to configure the `PyomoRuleBaseConfig`.

    Attributes:
        commodity_name (str): Name of the commodity being controlled (e.g., "hydrogen").
        commodity_units (str): Units of the commodity (e.g., "kg/h").
    """

    commodity_name: str = field()
    commodity_storage_units: str = field()


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

        raise NotImplementedError("This method should be implemented in a subclass.")

    def dispatch_block_rule_function(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
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
