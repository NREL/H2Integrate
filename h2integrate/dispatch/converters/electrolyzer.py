import pyomo.environ as pyo

from h2integrate.dispatch.dispatch_baseclass import PyomoDispatchBaseClass


class PyomoDispatchElectrolyzer(PyomoDispatchBaseClass):
    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        discrete_outputs["_create_port"] = self._create_port
        discrete_outputs["_create_variables"] = self._create_variables

        return

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
