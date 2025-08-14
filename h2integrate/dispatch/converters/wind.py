import pyomo.environ as pyo

from h2integrate.dispatch.dispatch_baseclass import PyomoDispatchBaseClass


class PyomoDispatchWind(PyomoDispatchBaseClass):
    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        discrete_outputs["_create_port"] = self._create_port
        discrete_outputs["_create_variables"] = self._create_variables

        return

    def _create_variables(self, pyomo_model):
        """Create wind variables to add to hybrid plant instance.

        Args:
            hybrid: Hybrid plant instance.

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

    def _create_port(self, pyomo_model):
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
