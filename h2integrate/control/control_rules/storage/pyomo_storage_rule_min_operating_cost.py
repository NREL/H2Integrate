import pyomo.environ as pyo
from pyomo.network import Port, Expression

from h2integrate.control.control_rules.storage.pyomo_storage_rule_baseclass import PyomoRuleStorageBaseclass


class PyomoRuleStorageMinOperatingCosts(PyomoRuleStorageBaseclass):
    """Base class defining PYomo rules for generic commodity storage components."""

    def initialize_parameters(self, commodity_in: list, commodity_demand: list):
        self.commodity_load_demand = [commodity_demand[t]
                                        for t in self.blocks.index_set()
                                        ]
        self.load_production_limit = [commodity_demand[t]
                                        for t in self.blocks.index_set()
                                        ]

    def _create_parameters(self, pyomo_model: pyo.ConcreteModel, t):
        """Create storage-related parameters in the Pyomo model.

        This method defines key storage parameters such as capacity limits,
        state-of-charge (SOC) bounds, efficiencies, and time duration for each
        time step.

        Args:
            pyomo_model (pyo.ConcreteModel): Pyomo model instance representing
                the storage system.
            t: Time index or iterable representing time steps (unused in this method).
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
        pyomo_model.cost_per_charge = pyo.Param(
            doc="Operating cost of " + pyomo_model.name + " charging [$/"
            + self.config.commodity_storage_units
            + "]",
            default=0.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units.USD / pyo.units." + self.config.commodity_storage_units),
        )
        pyomo_model.cost_per_discharge = pyo.Param(
            doc="Operating cost of " + pyomo_model.name + " discharging [$/"
            + self.config.commodity_storage_units
            + "]",
            default=0.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units.USD / pyo.units." + self.config.commodity_storage_units),
        )
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
        ##################################
        # System Parameters              #
        ##################################
        pyomo_model.epsilon = pyo.Param(
            doc="A small value used in objective for binary logic",
            default=1e-3,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=pyo.units.USD,
        )
        pyomo_model.commodity_met_value = pyo.Param(
            doc="Commodity demand met value per generation [$/"
            + self.config.commodity_storage_units
            + "]",
            default=0.0,
            within=pyo.Reals,
            mutable=True,
            units=eval("pyo.units.USD / pyo.units." + self.config.commodity_storage_units),
        )
        # grid.electricity_purchase_price = pyomo.Param(
        #     doc="Electricity purchase price [$/MWh]",
        #     default=0.0,
        #     within=pyomo.Reals,
        #     mutable=True,
        #     units=u.USD / u.MWh,
        # )
        pyomo_model.commodity_load_demand = pyo.Param(
            doc="Load demand for the commodity ["
            + self.config.commodity_storage_units
            + "]",
            default=1000.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )
        pyomo_model.load_production_limit = pyo.Param(
            doc="Production limit for load ["
            + self.config.commodity_storage_units
            + "]",
            default=1000.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )

    def _create_variables(self, pyomo_model: pyo.ConcreteModel, t):
        """Create storage-related decision variables in the Pyomo model.

        This method defines binary and continuous variables representing
        charging/discharging modes, energy flows, and state-of-charge.

        Args:
            pyomo_model (pyo.ConcreteModel): Pyomo model instance representing
                the storage system.
            t: Time index or iterable representing time steps (unused in this method).
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
        pyomo_model.system_production = pyo.Var(
            doc="System generation [MW]",
            domain=pyo.NonNegativeReals,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )
        pyomo_model.system_load = pyo.Var(
            doc="System load [MW]",
            domain=pyo.NonNegativeReals,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )
        pyomo_model.commodity_out = pyo.Var(
            doc="Electricity sold [MW]",
            domain=pyo.NonNegativeReals,
            bounds=(0, pyomo_model.commodity_load_demand),
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )
        pyomo_model.is_generating = pyo.Var(
            doc="System is generating power",
            domain=pyo.Binary,
            units=pyo.units.dimensionless
        )
        # TODO: Not needed for now, add back in later if needed
        # pyomo_model.electricity_purchased = pyo.Var(
        #     doc="Electricity purchased [MW]",
        #     domain=pyo.NonNegativeReals,
        #     units=u.MW,
        # )
        return (
            pyomo_model.discharge_commodity,
            pyomo_model.charge_commodity)

    def _create_constraints(self, pyomo_model: pyo.ConcreteModel, t):
        """Create operational and state-of-charge constraints for storage.

        This method defines constraints that enforce:
        - Mutual exclusivity between charging and discharging.
        - Upper and lower bounds on charge/discharge flows.
        - The state-of-charge balance over time.

        Args:
            pyomo_model (pyo.ConcreteModel): Pyomo model instance representing
                the storage system.
            t: Time index or iterable representing time steps (unused in this method).
        """
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

        pyomo_model.balance = pyo.Constraint(
            doc="Transmission energy balance",
            expr=(
                pyomo_model.commodity_out
                == pyomo_model.system_production - pyomo_model.system_load
            ),
        )
        pyomo_model.production_limit = pyo.Constraint(
            doc="Transmission limit on electricity sales",
            expr=pyomo_model.commodity_out
            <= pyomo_model.commodity_load_demand * pyomo_model.is_generating,
        )
        pyomo_model.production_link = pyo.Constraint()
        # pyomo_model.purchases_transmission_limit = pyomo.Constraint(
        #     doc="Transmission limit on electricity purchases",
        #     expr=(
        #         grid.electricity_purchased
        #         <= grid.load_transmission_limit * (1 - grid.is_generating)
        #     ),
        # )

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
        # Linking time periods together
        def storage_soc_linking_rule(m, t):
            if t == m.blocks.index_set().first():
                return m.blocks[t].soc0 == m.initial_soc
            return m.blocks[t].soc0 == self.blocks[t - 1].soc

        pyomo_model.soc_linking = pyo.Constraint(
            pyomo_model.blocks.index_set(),
            doc=self.block_set_name + " state-of-charge block linking constraint",
            rule=storage_soc_linking_rule,
        )

    def _create_ports(self, pyomo_model: pyo.ConcreteModel, t):
        """Create Pyomo ports for connecting the storage component.

        Ports are used to connect inflows and outflows of the storage system
        (e.g., charging and discharging commodities) to the overall Pyomo model.

        Args:
            pyomo_model (pyo.ConcreteModel): Pyomo model instance representing
                the storage system.
            t: Time index or iterable representing time steps (unused in this method).
        """
        ##################################
        # Ports                          #
        ##################################
        pyomo_model.port = Port()
        pyomo_model.port.add(pyomo_model.charge_commodity)
        pyomo_model.port.add(pyomo_model.discharge_commodity)
        pyomo_model.port.add(pyomo_model.system_production)
        pyomo_model.port.add(pyomo_model.system_load)
        pyomo_model.port.add(pyomo_model.commodity_out)
        # pyomo_model.port.add(pyomo_model.electricity_purchased)

    def update_time_series_parameters(self, start_time: int,
                                      commodity_in:list,
                                      commodity_demand:list,
                                      time_commodity_met_value:list
                                      ):
        """Update time series parameters method.

        Args:
            start_time (int): The starting time index for the update.
            commodity_in (list): List of commodity input values for each time step.
        """
        self.time_duration = [1.0] * len(self.blocks.index_set())
        self.commodity_load_demand = [commodity_demand[t]
                                        for t in self.blocks.index_set()]
        self.load_production_limit = [commodity_demand[t]
                                        for t in self.blocks.index_set()]
        self.commodity_met_value = [time_commodity_met_value[t]
                                        for t in self.blocks.index_set()]

    def min_operating_cost_objective(self, hybrid_blocks, tech_name: str):
        """Wind instance of minimum operating cost objective.

        Args:
            hybrid_blocks (Pyomo.block): A generalized container for defining hierarchical
                models by adding modeling components as attributes.

        """
        self.obj = Expression(
                        expr = sum(
                            hybrid_blocks[t].time_weighting_factor
                            * self.blocks[t].time_duration
                            * (
                                self.blocks[t].cost_per_discharge * self.blocks[t].charge_commodity[t]
                                - self.blocks[t].cost_per_charge * self.blocks[t].discharge_commodity[t]
                                + (self.blocks[t].commodity_load_demand[t]
                                - self.blocks[t].commodity_out
                                    ) * self.blocks[t].penalty_cost_per_unmet_demand
                            )  # Try to incentivize battery charging
                            for t in self.blocks.index_set()
                        )
                    )

    @property
    def commodity_load_demand(self) -> list:
        return [
            self.blocks[t].commodity_load_demand.value
            for t in self.blocks.index_set()
        ]

    @commodity_load_demand.setter
    def commodity_load_demand(self, commodity_demand: list):
        if len(commodity_demand) == len(self.blocks):
            for t, limit in zip(self.blocks, commodity_demand):
                self.blocks[t].commodity_load_demand.set_value(
                    round(limit, self.round_digits)
                )
        else:
            raise ValueError("'commodity_demand' list must be the same length as time horizon")

    @property
    def load_production_limit(self) -> list:
        return [
            self.blocks[t].load_production_limit.value
            for t in self.blocks.index_set()
        ]

    @load_production_limit.setter
    def load_production_limit(self, commodity_demand: list):
        if len(commodity_demand) == len(self.blocks):
            for t, limit in zip(self.blocks, commodity_demand):
                self.blocks[t].load_production_limit.set_value(
                    round(limit, self.round_digits)
                )
        else:
            raise ValueError("'commodity_demand' list must be the same length as time horizon")

    @property
    def commodity_met_value(self) -> list:
        return [
            self.blocks[t].commodity_met_value.value for t in self.blocks.index_set()
        ]

    @commodity_met_value.setter
    def commodity_met_value(self, price_per_kwh: list):
        if len(price_per_kwh) == len(self.blocks):
            for t, price in zip(self.blocks, price_per_kwh):
                self.blocks[t].commodity_met_value.set_value(
                    round(price, self.round_digits)
                )
        else:
            raise ValueError(
                "'price_per_kwh' list must be the same length as time horizon"
            )

    @property
    def system_production(self) -> list:
        return [self.blocks[t].system_production.value for t in self.blocks.index_set()]

    @property
    def system_load(self) -> list:
        return [self.blocks[t].system_load.value for t in self.blocks.index_set()]

    @property
    def commodity_out(self) -> list:
        return [self.blocks[t].commodity_out.value for t in self.blocks.index_set()]

    # @property
    # def electricity_purchased(self) -> list:
    #     return [
    #         self.blocks[t].electricity_purchased.value for t in self.blocks.index_set()
    #     ]

    @property
    def is_generating(self) -> list:
        return [self.blocks[t].is_generating.value for t in self.blocks.index_set()]

    @property
    def not_generating(self) -> list:
        return [self.blocks[t].not_generating.value for t in self.blocks.index_set()]