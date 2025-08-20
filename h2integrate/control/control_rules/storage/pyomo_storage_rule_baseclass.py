import pyomo.environ as pyo
from pyomo.network import Port

from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseClass


class PyomoRuleStorageBaseclass(PyomoRuleBaseClass):
    def _create_parameters(self, storage):
        """Creates storage parameters.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Storage Parameters             #
        ##################################
        storage.time_duration = pyo.Param(
            doc="Time step [hour]",
            default=1.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=pyo.units.hr,
        )
        # storage.cost_per_charge = pyo.Param(
        #     doc="Operating cost of " + self.block_set_name + " charging [$/MWh]",
        #     default=0.0,
        #     within=pyo.NonNegativeReals,
        #     mutable=True,
        #     units=pyo.units.USD / pyo.units.MWh,
        # )
        # storage.cost_per_discharge = pyo.Param(
        #     doc="Operating cost of " + self.block_set_name + " discharging [$/MWh]",
        #     default=0.0,
        #     within=pyo.NonNegativeReals,
        #     mutable=True,
        #     units=pyo.units.USD / pyo.units.MWh,
        # )
        storage.minimum_storage = pyo.Param(
            doc=self.block_set_name
            + " minimum storage rating ["
            + self.config.resource_units
            + "]",
            default=0.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.resource_units),
        )
        storage.maximum_storage = pyo.Param(
            doc=self.block_set_name
            + " maximum storage rating ["
            + self.config.resource_units
            + "]",
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.resource_units),
        )
        storage.minimum_soc = pyo.Param(
            doc=self.block_set_name + " minimum state-of-charge [-]",
            default=0.1,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )
        storage.maximum_soc = pyo.Param(
            doc=self.block_set_name + " maximum state-of-charge [-]",
            default=0.9,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )

        ##################################
        # Efficiency Parameters          #
        ##################################
        storage.charge_efficiency = pyo.Param(
            doc=self.block_set_name + " Charging efficiency [-]",
            default=0.938,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )
        storage.discharge_efficiency = pyo.Param(
            doc=self.block_set_name + " discharging efficiency [-]",
            default=0.938,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )
        ##################################
        # Capacity Parameters            #
        ##################################

        storage.capacity = pyo.Param(
            doc=self.block_set_name + " capacity [" + self.config.resource_rate_units + "]",
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.resource_rate_units),
        )

    def _create_variables(self, storage):
        """Creates storage variables.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Variables                      #
        ##################################
        storage.is_charging = pyo.Var(
            doc="1 if " + self.block_set_name + " is charging; 0 Otherwise [-]",
            domain=pyo.Binary,
            units=pyo.units.dimensionless,
        )
        storage.is_discharging = pyo.Var(
            doc="1 if " + self.block_set_name + " is discharging; 0 Otherwise [-]",
            domain=pyo.Binary,
            units=pyo.units.dimensionless,
        )
        storage.soc0 = pyo.Var(
            doc=self.block_set_name + " initial state-of-charge at beginning of period[-]",
            domain=pyo.PercentFraction,
            bounds=(storage.minimum_soc, storage.maximum_soc),
            units=pyo.units.dimensionless,
        )
        storage.soc = pyo.Var(
            doc=self.block_set_name + " state-of-charge at end of period [-]",
            domain=pyo.PercentFraction,
            bounds=(storage.minimum_soc, storage.maximum_soc),
            units=pyo.units.dimensionless,
        )
        storage.charge_resource = pyo.Var(
            doc=self.config.resource_name
            + " into "
            + self.block_set_name
            + " ["
            + self.config.resource_units
            + "]",
            domain=pyo.NonNegativeReals,
            units=eval("pyo.units." + self.config.resource_units),
        )
        storage.discharge_resource = pyo.Var(
            doc=self.config.resource_name
            + " out of "
            + self.block_set_name
            + " ["
            + self.config.resource_units
            + "]",
            domain=pyo.NonNegativeReals,
            units=eval("pyo.units." + self.config.resource_units),
        )

    def _create_constraints(self, storage):
        ##################################
        # Charging Constraints           #
        ##################################
        # Charge power bounds
        storage.charge_resource_ub = pyo.Constraint(
            doc=self.block_set_name + " charging storage upper bound",
            expr=storage.charge_resource <= storage.maximum_storage * storage.is_charging,
        )
        storage.charge_resource_lb = pyo.Constraint(
            doc=self.block_set_name + " charging storage lower bound",
            expr=storage.charge_resource >= storage.minimum_storage * storage.is_charging,
        )
        # Discharge power bounds
        storage.discharge_resource_lb = pyo.Constraint(
            doc=self.block_set_name + " Discharging storage lower bound",
            expr=storage.discharge_resource >= storage.minimum_storage * storage.is_discharging,
        )
        storage.discharge_resource_ub = pyo.Constraint(
            doc=self.block_set_name + " Discharging storage upper bound",
            expr=storage.discharge_resource <= storage.maximum_storage * storage.is_discharging,
        )
        # Storage packing constraint
        storage.charge_discharge_packing = pyo.Constraint(
            doc=self.block_set_name + " packing constraint for charging and discharging binaries",
            expr=storage.is_charging + storage.is_discharging <= 1,
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
        storage.soc_inventory = pyo.Constraint(
            doc=self.block_set_name + " state-of-charge inventory balance",
            rule=soc_inventory_rule,
        )

    @staticmethod
    def _create_ports(storage):
        """Creates storage port.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Ports                          #
        ##################################
        storage.port = Port()
        storage.port.add(storage.charge_resource)
        storage.port.add(storage.discharge_resource)
