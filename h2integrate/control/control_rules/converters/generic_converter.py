import pyomo.environ as pyo
from pyomo.network import Port

from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseClass


class PyomoDispatchGenericConverter(PyomoRuleBaseClass):
    def _create_variables(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create generic generator variables to add to pyomo model instance.

        Args:
            pyomo_model: pyomo_model the variables should be added to.

        """
        setattr(
            pyomo_model,
            f"{tech_name}_{self.config.commodity_name}",
            pyo.Var(
                doc=f"{self.config.commodity_name} generation \
                    from {tech_name} [{self.config.commodity_storage_units}]",
                domain=pyo.NonNegativeReals,
                units=eval("pyo.units." + self.config.commodity_storage_units),
                initialize=0.0,
            ),
        )

    def _create_ports(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create generic converter port to add to pyomo model instance.

        Args:
            pyomo_model: pyomo_model the ports should be added to.

        """
        setattr(
            pyomo_model,
            f"{tech_name}_port",
            Port(
                initialize={
                    f"{tech_name}_{self.config.commodity_name}": getattr(
                        pyomo_model, f"{tech_name}_{self.config.commodity_name}"
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
