import pyomo.environ as pyo

from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseClass


class PyomoDispatchWind(PyomoRuleBaseClass):
    def _create_variables(self, pyomo_model):
        """Create wind variables to add to pyomo model hybrid plant instance.

        Args:
            pyomo_model: Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
                - generation: Generation from given technology.
                - load: Load from given technology.

        """
        pyomo_model.wind_electricity = pyo.Var(
            doc="Electricity generation from wind turbines [MW]",
            domain=pyo.NonNegativeReals,
            units=pyo.units.MW,
            initialize=0.0,
        )
        return pyomo_model.wind_electricity, 0

    def _create_ports(self, pyomo_model):
        """Create wind port to add to hybrid plant instance.

        Args:
            hybrid: Hybrid plant instance.

        Returns:
            Port: Wind Port object.

        """
        pyomo_model.wind_port = pyo.Port(
            initialize={"wind_electricity": pyomo_model.wind_electricity}
        )
        return pyomo_model.wind_port

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
