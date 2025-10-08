import pyomo.environ as pyo
from pyomo.network import Port

from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseClass


class PyomoDispatchGenericConvertor(PyomoRuleBaseClass):
    def _create_variables(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create electricity generator variables to add to pyomo model hybrid plant instance.

        Args:
            pyomo_model: Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
                - generation: Generation from given technology.
                - load: Load from given technology.

        """
        setattr(
            pyomo_model,
            f"{tech_name}_electricity",
            pyo.Var(
                doc=f"{self.config.commodity_name} generation from wind turbines [MW]",
                domain=pyo.NonNegativeReals,
                units=eval("pyo.units." + self.config.commodity_storage_units),
                initialize=0.0,
            ),
        )

    def _create_ports(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create wind port to add to hybrid plant instance.

        Args:
            hybrid: Hybrid plant instance.

        Returns:
            Port: Wind Port object.

        """
        setattr(
            pyomo_model,
            f"{tech_name}_port",
            Port(
                initialize={
                    f"{tech_name}_{self.config.commodity_name}": getattr(
                        pyomo_model, f"{tech_name}_electricity"
                    )
                }
            ),
        )

    def _create_parameters(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create technology Pyomo parameters to add to the Pyomo model instance.

        Args:
            pyomo_model: Pyomo Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
        """

        pass

    def _create_constraints(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create technology Pyomo parameters to add to the Pyomo model instance.

        Args:
            pyomo_model: Pyomo Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
        """

        pass
