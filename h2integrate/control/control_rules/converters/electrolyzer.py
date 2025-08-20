import pyomo.environ as pyo

from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseClass


class PyomoDispatchElectrolyzer(PyomoRuleBaseClass):
    def _create_variables(self, pyomo_model):
        """Create pyomo electrolyzer variables to add to hybrid plant instance.

        Args:
            hybrid: Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
                - generation: Generation from given technology.
                - load: Load from given technology.

        """
        pyomo_model.electrolyzer_hydrogen = pyo.Var(
            doc="Hydrogen generation from electrolysis [kg]",
            domain=pyo.NonNegativeReals,
            units=pyo.units.kg,
            initialize=0.0,
        )
        return pyomo_model.electrolyzer_hydrogen, 0

    def _create_port(self, pyomo_model):
        """Create electrolyzer port to add to hybrid plant instance.

        Args:
            hybrid: Hybrid plant instance.

        Returns:
            Port: Wind Port object.

        """
        pyomo_model.electrolyzer_port = pyo.Port(
            initialize={"electrolyzer_hydrogen": pyomo_model.electrolyzer_hydrogen}
        )
        return pyomo_model.electrolyzer_port

    def _create_parameters(self, pyomo_model):
        """Create technology Pyomo parameters to add to the Pyomo model instance.

        Args:
            pyomo_model: Pyomo Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
        """

        pass

    def _create_constraints(self, pyomo_model):
        """Create technology Pyomo parameters to add to the Pyomo model instance.

        Args:
            pyomo_model: Pyomo Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
        """

        pass
