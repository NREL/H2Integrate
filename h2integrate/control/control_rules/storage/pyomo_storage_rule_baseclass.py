import pyomo.environ as pyo
from pyomo.network import Port

from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseClass


class PyomoRuleStorageBaseclass(PyomoRuleBaseClass):
    def _create_parameters(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Creates storage parameters.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Storage Parameters             #
        ##################################
        pyomo_model.time_duration = pyo.Param(
            doc=tech_name + " Time step [hour]",
            default=1.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=pyo.units.hr,
        )
        # pyomo_model.cost_per_charge = pyo.Param(
        #     doc="Operating cost of " + self.block_set_name + " charging [$/MWh]",
        #     default=0.0,
        #     within=pyo.NonNegativeReals,
        #     mutable=True,
        #     units=pyo.units.USD / pyo.units.MWh,
        # )
        # pyomo_model.cost_per_discharge = pyo.Param(
        #     doc="Operating cost of " + self.block_set_name + " discharging [$/MWh]",
        #     default=0.0,
        #     within=pyo.NonNegativeReals,
        #     mutable=True,
        #     units=pyo.units.USD / pyo.units.MWh,
        # )
        pyomo_model.minimum_storage = pyo.Param(
            doc=self.block_set_name
            + tech_name
            + " minimum storage rating ["
            + self.config.resource_units
            + "]",
            default=0.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.resource_units),
        )
        pyomo_model.maximum_storage = pyo.Param(
            doc=self.block_set_name
            + tech_name
            + " maximum storage rating ["
            + self.config.resource_units
            + "]",
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.resource_units),
        )
        pyomo_model.minimum_soc = pyo.Param(
            doc=self.block_set_name + tech_name + " minimum state-of-charge [-]",
            default=0.1,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )
        pyomo_model.maximum_soc = pyo.Param(
            doc=self.block_set_name + tech_name + " maximum state-of-charge [-]",
            default=0.9,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )

        ##################################
        # Efficiency Parameters          #
        ##################################
        pyomo_model.charge_efficiency = pyo.Param(
            doc=self.block_set_name + tech_name + " Charging efficiency [-]",
            default=0.938,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )
        pyomo_model.discharge_efficiency = pyo.Param(
            doc=self.block_set_name + tech_name + " discharging efficiency [-]",
            default=0.938,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )
        ##################################
        # Capacity Parameters            #
        ##################################

        pyomo_model.capacity = pyo.Param(
            doc=self.block_set_name
            + tech_name
            + " capacity ["
            + self.config.resource_rate_units
            + "]",
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.resource_rate_units),
        )

    def _create_variables(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Creates storage variables.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Variables                      #
        ##################################
        pyomo_model.is_charging = pyo.Var(
            doc="1 if " + self.block_set_name + tech_name + " is charging; 0 Otherwise [-]",
            domain=pyo.Binary,
            units=pyo.units.dimensionless,
        )
        pyomo_model.is_discharging = pyo.Var(
            doc="1 if " + self.block_set_name + tech_name + " is discharging; 0 Otherwise [-]",
            domain=pyo.Binary,
            units=pyo.units.dimensionless,
        )
        pyomo_model.soc0 = pyo.Var(
            doc=self.block_set_name
            + tech_name
            + " initial state-of-charge at beginning of period[-]",
            domain=pyo.PercentFraction,
            bounds=(pyomo_model.minimum_soc, pyomo_model.maximum_soc),
            units=pyo.units.dimensionless,
        )
        pyomo_model.soc = pyo.Var(
            doc=self.block_set_name + tech_name + " state-of-charge at end of period [-]",
            domain=pyo.PercentFraction,
            bounds=(pyomo_model.minimum_soc, pyomo_model.maximum_soc),
            units=pyo.units.dimensionless,
        )
        pyomo_model.charge_resource = pyo.Var(
            doc=self.config.resource_name
            + " into "
            + self.block_set_name
            + tech_name
            + " ["
            + self.config.resource_units
            + "]",
            domain=pyo.NonNegativeReals,
            units=eval("pyo.units." + self.config.resource_units),
        )
        pyomo_model.discharge_resource = pyo.Var(
            doc=self.config.resource_name
            + " out of "
            + self.block_set_name
            + tech_name
            + " ["
            + self.config.resource_units
            + "]",
            domain=pyo.NonNegativeReals,
            units=eval("pyo.units." + self.config.resource_units),
        )

    def _create_constraints(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        ##################################
        # Charging Constraints           #
        ##################################
        # Charge power bounds
        pyomo_model.charge_resource_ub = pyo.Constraint(
            doc=self.block_set_name + tech_name + " charging storage upper bound",
            expr=pyomo_model.charge_resource
            <= pyomo_model.maximum_storage * pyomo_model.is_charging,
        )
        pyomo_model.charge_resource_lb = pyo.Constraint(
            doc=self.block_set_name + tech_name + " charging storage lower bound",
            expr=pyomo_model.charge_resource
            >= pyomo_model.minimum_storage * pyomo_model.is_charging,
        )
        # Discharge power bounds
        pyomo_model.discharge_resource_lb = pyo.Constraint(
            doc=self.block_set_name + tech_name + " Discharging storage lower bound",
            expr=pyomo_model.discharge_resource
            >= pyomo_model.minimum_storage * pyomo_model.is_discharging,
        )
        pyomo_model.discharge_resource_ub = pyo.Constraint(
            doc=self.block_set_name + tech_name + " Discharging storage upper bound",
            expr=pyomo_model.discharge_resource
            <= pyomo_model.maximum_storage * pyomo_model.is_discharging,
        )
        # Storage packing constraint
        pyomo_model.charge_discharge_packing = pyo.Constraint(
            doc=self.block_set_name
            + tech_name
            + " packing constraint for charging and discharging binaries",
            expr=pyomo_model.is_charging + pyomo_model.is_discharging <= 1,
        )

        ##################################
        # SOC Inventory Constraints      #
        ##################################

        def soc_inventory_rule(m):
            return m.soc == (
                m.soc0
                + m.time_duration
                * (
                    m.charge_efficiency * m.charge_resource
                    - (1 / m.discharge_efficiency) * m.discharge_resource
                )
                / m.capacity
            )

        # Storage State-of-charge balance
        pyomo_model.soc_inventory = pyo.Constraint(
            doc=self.block_set_name + tech_name + " state-of-charge inventory balance",
            rule=soc_inventory_rule,
        )

    @staticmethod
    def _create_ports(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Creates storage port.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Ports                          #
        ##################################
        pyomo_model.port = Port()
        pyomo_model.port.add(pyomo_model.charge_resource)
        pyomo_model.port.add(pyomo_model.discharge_resource)
