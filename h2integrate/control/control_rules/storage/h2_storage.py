import pyomo.environ as pyo

from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseClass


class PyomoDispatchH2Storage(PyomoRuleBaseClass):
    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        discrete_outputs["_create_variables"] = self._create_variables
        discrete_outputs["_create_port"] = self._create_port

        return

    def _create_variables(self, pyomo_model):
        """Creates storage variables for hydrogen.

        Args:
            hybrid: Hybrid instance.

        Returns:
            Tuple: Tuple containing battery discharge and charge variables.

        """
        pyomo_model.hydrogen_charge = pyo.Var(
            doc="Charging the hydrogen storage [kg]",
            domain=pyo.NonNegativeReals,
            units=pyo.units.kg,
            initialize=0.0,
        )
        pyomo_model.hydrogen_discharge = pyo.Var(
            doc="Discharging the hydrogen storage [kg]",
            domain=pyo.NonNegativeReals,
            units=pyo.units.kg,
            initialize=0.0,
        )
        return pyomo_model.hydrogen_discharge, pyomo_model.hydrogen_charge

    def _create_port(self, pyomo_model):
        """Creates storage port.

        Args:
            hybrid: pyomo model of the hybrid system.

        Returns:
            Port: Storage port.

        """
        pyomo_model.hydrogen_storage_port = pyo.Port(
            initialize={
                "charge_power": pyomo_model.hydrogen_charge,
                "discharge_power": pyomo_model.hydrogen_discharge,
            }
        )
        return pyomo_model.hydrogen_storage_port
