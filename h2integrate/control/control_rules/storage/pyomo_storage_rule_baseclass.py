import pyomo.environ as pyo
from pyomo.network import Port

from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseClass


class PyomoRuleStorageBaseclass(PyomoRuleBaseClass):
    def _create_parameters(self, pyomo_model: pyo.ConcreteModel, t):
        """Creates storage parameters.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Storage Parameters             #
        ##################################
        pyomo_model.time_duration = pyo.Param(
            doc=pyomo_model.name + " time step [hour]",
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
            doc=pyomo_model.name
            + " minimum storage rating ["
            + self.config.commodity_storage_units
            + "]",
            default=0.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )
        pyomo_model.maximum_storage = pyo.Param(
            doc=pyomo_model.name
            + " maximum storage rating ["
            + self.config.commodity_storage_units
            + "]",
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )
        pyomo_model.minimum_soc = pyo.Param(
            doc=pyomo_model.name + " minimum state-of-charge [-]",
            default=0.1,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )
        pyomo_model.maximum_soc = pyo.Param(
            doc=pyomo_model.name + " maximum state-of-charge [-]",
            default=0.9,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )

        ##################################
        # Efficiency Parameters          #
        ##################################
        pyomo_model.charge_efficiency = pyo.Param(
            doc=pyomo_model.name + " Charging efficiency [-]",
            default=0.938,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )
        pyomo_model.discharge_efficiency = pyo.Param(
            doc=pyomo_model.name + " discharging efficiency [-]",
            default=0.938,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )
        ##################################
        # Capacity Parameters            #
        ##################################

        pyomo_model.capacity = pyo.Param(
            doc=pyomo_model.name + " capacity [" + self.config.commodity_storage_units + "]",
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )

    def _create_variables(self, pyomo_model: pyo.ConcreteModel, t):
        """Creates storage variables.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Variables                      #
        ##################################
        pyomo_model.is_charging = pyo.Var(
            doc="1 if " + pyomo_model.name + " is charging; 0 Otherwise [-]",
            domain=pyo.Binary,
            units=pyo.units.dimensionless,
        )
        pyomo_model.is_discharging = pyo.Var(
            doc="1 if " + pyomo_model.name + " is discharging; 0 Otherwise [-]",
            domain=pyo.Binary,
            units=pyo.units.dimensionless,
        )
        pyomo_model.soc0 = pyo.Var(
            doc=pyomo_model.name + " initial state-of-charge at beginning of period[-]",
            domain=pyo.PercentFraction,
            bounds=(pyomo_model.minimum_soc, pyomo_model.maximum_soc),
            units=pyo.units.dimensionless,
        )
        pyomo_model.soc = pyo.Var(
            doc=pyomo_model.name + " state-of-charge at end of period [-]",
            domain=pyo.PercentFraction,
            bounds=(pyomo_model.minimum_soc, pyomo_model.maximum_soc),
            units=pyo.units.dimensionless,
        )
        pyomo_model.charge_commodity = pyo.Var(
            doc=self.config.commodity_name
            + " into "
            + pyomo_model.name
            + " ["
            + self.config.commodity_storage_units
            + "]",
            domain=pyo.NonNegativeReals,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )
        pyomo_model.discharge_commodity = pyo.Var(
            doc=self.config.commodity_name
            + " out of "
            + pyomo_model.name
            + " ["
            + self.config.commodity_storage_units
            + "]",
            domain=pyo.NonNegativeReals,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )

    def _create_constraints(self, pyomo_model: pyo.ConcreteModel, t):
        ##################################
        # Charging Constraints           #
        ##################################
        # Charge commodity bounds
        pyomo_model.charge_commodity_ub = pyo.Constraint(
            doc=pyomo_model.name + " charging storage upper bound",
            expr=pyomo_model.charge_commodity
            <= pyomo_model.maximum_storage * pyomo_model.is_charging,
        )
        pyomo_model.charge_commodity_lb = pyo.Constraint(
            doc=pyomo_model.name + " charging storage lower bound",
            expr=pyomo_model.charge_commodity
            >= pyomo_model.minimum_storage * pyomo_model.is_charging,
        )
        # Discharge commodity bounds
        pyomo_model.discharge_commodity_lb = pyo.Constraint(
            doc=pyomo_model.name + " Discharging storage lower bound",
            expr=pyomo_model.discharge_commodity
            >= pyomo_model.minimum_storage * pyomo_model.is_discharging,
        )
        pyomo_model.discharge_commodity_ub = pyo.Constraint(
            doc=pyomo_model.name + " Discharging storage upper bound",
            expr=pyomo_model.discharge_commodity
            <= pyomo_model.maximum_storage * pyomo_model.is_discharging,
        )
        # Storage packing constraint
        pyomo_model.charge_discharge_packing = pyo.Constraint(
            doc=pyomo_model.name + " packing constraint for charging and discharging binaries",
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
                    m.charge_efficiency * m.charge_commodity
                    - (1 / m.discharge_efficiency) * m.discharge_commodity
                )
                / m.capacity
            )

        # Storage State-of-charge balance
        pyomo_model.soc_inventory = pyo.Constraint(
            doc=pyomo_model.name + " state-of-charge inventory balance",
            rule=soc_inventory_rule,
        )

        ##################################
        # SOC Linking Constraints        #
        ##################################

        # TODO: Make work for pyomo optimization, not needed for heuristic method
        # # Linking time periods together
        # def storage_soc_linking_rule(m, t):
        #     if t == m.blocks.index_set().first():
        #         return m.blocks[t].soc0 == m.initial_soc
        #     return m.blocks[t].soc0 == self.blocks[t - 1].soc

        # pyomo_model.soc_linking = pyo.Constraint(
        #     pyomo_model.blocks.index_set(),
        #     doc=self.block_set_name + " state-of-charge block linking constraint",
        #     rule=storage_soc_linking_rule,
        # )

    def _create_ports(self, pyomo_model: pyo.ConcreteModel, t):
        """Creates storage port.

        Args:
            pyomo_model: Pyomo storage instance.

        """
        ##################################
        # Ports                          #
        ##################################
        pyomo_model.port = Port()
        pyomo_model.port.add(pyomo_model.charge_commodity)
        pyomo_model.port.add(pyomo_model.discharge_commodity)
