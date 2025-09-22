from typing import TYPE_CHECKING

import numpy as np
import pyomo.environ as pyomo
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.control.control_strategies.controller_baseclass import ControllerBaseClass


if TYPE_CHECKING:  # to avoid circular imports
    pass


@define
class PyomoControllerBaseConfig(BaseConfig):
    """
    Configuration class for the DemandOpenLoopController.

    This class defines the parameters required to configure the `DemandOpenLoopController`.

    Attributes:
        commodity_name (str): Name of the resource being controlled (e.g., "hydrogen").
        commodity_storage_units (str): Units of the resource (e.g., "kg/h").
        max_capacity (float): Maximum storage capacity of the resource (in non-rate units,
            e.g., "kg" if `commodity_rate_units` is "kg/h").
        max_charge_percent (float): Maximum allowable state of charge (SOC) as a percentage
            of `max_capacity`, represented as a decimal between 0 and 1.
        min_charge_percent (float): Minimum allowable SOC as a percentage of `max_capacity`,
            represented as a decimal between 0 and 1.
        init_charge_percent (float): Initial SOC as a percentage of `max_capacity`, represented
            as a decimal between 0 and 1.
        max_charge_rate (float): Maximum rate at which the resource can be charged (in units
            per time step, e.g., "kg/time step").
        max_discharge_rate (float): Maximum rate at which the resource can be discharged (in
            units per time step, e.g., "kg/time step").
        charge_efficiency (float): Efficiency of charging the storage, represented as a decimal
            between 0 and 1 (e.g., 0.9 for 90% efficiency).
        discharge_efficiency (float): Efficiency of discharging the storage, represented as a
            decimal between 0 and 1 (e.g., 0.9 for 90% efficiency).
    """

    max_capacity: float = field()
    max_charge_percent: float = field()
    min_charge_percent: float = field()
    init_charge_percent: float = field()
    n_control_window: int = field()
    n_horizon_window: int = field()
    commodity_name: str = field()
    commodity_storage_units: str = field()
    tech_name: str = field()


def dummy_function():
    return None


class PyomoControllerBaseClass(ControllerBaseClass):
    def dummy_method(self, in1, in2):
        return None

    def setup(self):
        # get technology group name
        # TODO: Make this more general, right now it might go astray if for example "battery" is
        # used twice in an OpenMDAO subsystem pathname
        self.tech_group_name = self.pathname.split(".")

        # create inputs for all pyomo object creation functions from all connected technologies
        self.dispatch_connections = self.options["plant_config"]["tech_to_dispatch_connections"]
        for connection in self.dispatch_connections:
            source_tech, intended_dispatch_tech = connection
            if any(intended_dispatch_tech in name for name in self.tech_group_name):
                if source_tech == intended_dispatch_tech:
                    # When getting rules for the same tech, the tech name is not used in order to
                    # allow for automatic connections rather than complicating the h2i model set up
                    self.add_discrete_input("dispatch_block_rule_function", val=self.dummy_method)
                else:
                    self.add_discrete_input(
                        f"{'dispatch_block_rule_function'}_{source_tech}", val=self.dummy_method
                    )
            else:
                continue

        # create output for the pyomo control model
        self.add_discrete_output(
            "pyomo_dispatch_solver",
            val=dummy_function,
            desc="callable: fully formed pyomo model and execution logic to be run \
                by owning technologies performance model",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        discrete_outputs["pyomo_dispatch_solver"] = self.pyomo_setup(discrete_inputs)

    def pyomo_setup(self, discrete_inputs):
        # initialize the pyomo model
        self.pyomo_model = pyomo.ConcreteModel()

        index_set = pyomo.Set(initialize=range(self.config.n_control_window))

        # run each pyomo rule set up function for each technology
        for connection in self.dispatch_connections:
            source_tech, intended_dispatch_tech = connection
            if any(intended_dispatch_tech in name for name in self.tech_group_name):
                if source_tech == intended_dispatch_tech:
                    dispatch_block_rule_function = discrete_inputs["dispatch_block_rule_function"]
                else:
                    dispatch_block_rule_function = discrete_inputs[
                        f"{'dispatch_block_rule_function'}_{source_tech}"
                    ]
                blocks = pyomo.Block(index_set, rule=dispatch_block_rule_function)
                setattr(self.pyomo_model, source_tech, blocks)
            else:
                continue

        # define dispatch solver
        def pyomo_dispatch_solver(
            performance_model: callable,
            performance_model_kwargs,
            inputs,
            pyomo_model=self.pyomo_model,
        ):
            self.initialize_parameters()

            # initialize outputs
            unmet_demand = np.zeros(self.n_timesteps)
            storage_commodity_out = np.zeros(self.n_timesteps)
            total_commodity_out = np.zeros(self.n_timesteps)
            excess_resource = np.zeros(self.n_timesteps)
            soc = np.zeros(self.n_timesteps)

            ti = list(range(0, self.n_timesteps, self.config.n_control_window))

            control_strategy = self.options["tech_config"]["control_strategy"]["model"]

            for t in ti:
                self.update_time_series_parameters()

                commodity_in = inputs[self.config.commodity_name + "_in"][
                    t : t + self.config.n_control_window
                ]
                demand_in = inputs["demand_in"][t : t + self.config.n_control_window]

                if "heuristic" in control_strategy:
                    self.set_fixed_dispatch(
                        commodity_in,
                        self.config.max_charge_rate,
                        self.config.max_discharge_rate,
                        demand_in,
                    )

                else:
                    raise (
                        NotImplementedError(
                            f"Control strategy '{control_strategy}' was given, \
                            but has not been implemented yet."
                        )
                    )
                    # TODO: implement optimized solutions; this is where pyomo_model would be used

                storage_commodity_out_control_window, soc_control_window = performance_model(
                    self.storage_dispatch_commands,
                    **performance_model_kwargs,
                    sim_start_index=t,
                )

                # store output values for every timestep
                tj = list(range(t, t + self.config.n_control_window))
                for j in tj:
                    storage_commodity_out[j] = storage_commodity_out_control_window[j - t]
                    soc[j] = soc_control_window[j - t]
                    total_commodity_out[j] = np.minimum(
                        demand_in[j - t], storage_commodity_out[j] + commodity_in[j - t]
                    )
                    unmet_demand[j] = np.maximum(0, demand_in[j - t] - total_commodity_out[j])
                    excess_resource[j] = np.maximum(0, commodity_in[j - t] - total_commodity_out[j])

            return total_commodity_out, storage_commodity_out, unmet_demand, excess_resource, soc

        return pyomo_dispatch_solver

    # def enforce_SOC_limits_pre_sim(self, resource_in, resource_chargeable, SOC, demand_in):
    #     # If discharging...
    #     if resource_in[t] > 0.0:
    #         # If the battery has been discharged to its minimum SOC level (with a tolerance)
    #         if (self.system_model.value("SOC") - self.system_model.value("minimum_SOC")) < 0.05:
    #             self.unmet_demand = demand_in[t]
    #             # Avoid trickle power by setting to 0.0
    #             resource_in[t] = 0.0

    #     # If charging...
    #     elif resource_in[t] < 0.0:
    #         # If the input electricity magnitude is greater than the battery chargeable capacity
    #         if resource_in[t] < P_chargeable:
    #             # Eliminates trickle power (~10-15 kW) when battery is fully charged
    #             if P_chargeable > 0.0:
    #                 P_chargeable = 0.0

    #             # Change the sign to indicate that a positive amount of power is being
    #             # passed through the battery model
    #             self.excess_resource = -1 * (resource_in[t] - P_chargeable)
    #             # Limit the charging power to the availabile capacity of the battery
    #             resource_in[t] = P_chargeable

    @staticmethod
    def dispatch_block_rule(block, t):
        raise NotImplementedError("This function must be overridden for specific dispatch model")

    def initialize_parameters(self):
        raise NotImplementedError("This function must be overridden for specific dispatch model")

    def update_time_series_parameters(self, start_time: int):
        raise NotImplementedError("This function must be overridden for specific dispatch model")

    @staticmethod
    def _check_efficiency_value(efficiency):
        """Checks efficiency is between 0 and 1. Returns fractional value"""
        if efficiency < 0:
            raise ValueError("Efficiency value must greater than 0")
        elif efficiency > 1:
            raise ValueError("Efficiency value must between 0 and 1")
        return efficiency

    @property
    def blocks(self) -> pyomo.Block:
        # TODO: Is there a way to inherit the correct tech name so it doesn't have to be defined
        # in the input config?
        return getattr(self.pyomo_model, self.config.tech_name)

    @property
    def model(self) -> pyomo.ConcreteModel:
        return self._model


@define
class PyomoControllerH2StorageConfig(PyomoControllerBaseConfig):
    """
    Configuration class for the PyomoControllerH2Storage.

    This class defines the parameters required to configure the `PyomoControllerH2Storage`.

    Attributes:
        max_charge_rate (float): Maximum rate at which the resource can be charged (in units
            per time step, e.g., "kg/time step").
        max_discharge_rate (float): Maximum rate at which the resource can be discharged (in
            units per time step, e.g., "kg/time step").
        charge_efficiency (float): Efficiency of charging the storage, represented as a decimal
            between 0 and 1 (e.g., 0.9 for 90% efficiency).
        discharge_efficiency (float): Efficiency of discharging the storage, represented as a
            decimal between 0 and 1 (e.g., 0.9 for 90% efficiency).
    """

    max_charge_rate: float = field()
    max_discharge_rate: float = field()
    charge_efficiency: float = field()
    discharge_efficiency: float = field()


class PyomoControllerH2Storage(PyomoControllerBaseClass):
    def setup(self):
        self.config = PyomoControllerH2StorageConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )
        super().setup()


class SimpleBatteryControllerHeuristic(PyomoControllerBaseClass):
    """Fixes battery dispatch operations based on user input.

    Currently, enforces available generation and grid limit assuming no battery charging from grid.

    """

    def setup(self):
        """Initialize SimpleBatteryControllerHeuristic.

        Args:
            pyomo_model (pyomo.ConcreteModel): Pyomo concrete model.
            index_set (pyomo.Set): Indexed set.
            system_model (PySAMBatteryModel.BatteryStateful): Battery system model.
            fixed_dispatch (Optional[List], optional): List of normalized values [-1, 1]
                (Charging (-), Discharging (+)). Defaults to None.
            block_set_name (str, optional): Name of block set. Defaults to 'heuristic_battery'.
            control_options (dict, optional): Dispatch options. Defaults to None.

        """
        super().setup()

        # self._create_soc_linking_constraint()

        # TODO: implement and test lifecycle counting
        # TODO: we could remove this option and just have lifecycle count default
        # self.control_options = control_options
        # if self.control_options.include_lifecycle_count:
        #     self._create_lifecycle_model()
        #     if self.control_options.max_lifecycle_per_day < np.inf:
        #         self._create_lifecycle_count_constraint()

        self.round_digits = 4

        self.max_charge_fraction = [0.0] * self.config.n_control_window
        self.max_discharge_fraction = [0.0] * self.config.n_control_window
        self._fixed_dispatch = [0.0] * self.config.n_control_window

        # TODO: should I enforce either a day schedule or a year schedule year and save it as
        # user input? Additionally, Should I drop it as input in the init function?
        # if fixed_dispatch is not None:
        #     self.user_fixed_dispatch = fixed_dispatch

    def initialize_parameters(self):
        """Initializes parameters."""
        # TODO: implement and test lifecycle counting
        # if self.config.include_lifecycle_count:
        #     self.lifecycle_cost = (
        #         self.options.lifecycle_cost_per_kWh_cycle
        #         * self._system_model.value("nominal_energy")
        #     )

        # self.cost_per_charge = self._financial_model.value("om_batt_variable_cost")[
        #     0
        # ]  # [$/MWh]
        # self.cost_per_discharge = self._financial_model.value("om_batt_variable_cost")[
        #     0
        # ]  # [$/MWh]
        self.minimum_storage = 0.0
        self.maximum_storage = self.config.max_capacity
        self.minimum_soc = self.config.min_charge_percent
        self.maximum_soc = self.config.max_charge_percent
        self.initial_soc = self.config.init_charge_percent

    # def _create_soc_linking_constraint(self):
    #     """Creates state-of-charge linking constraint."""
    #     ##################################
    #     # Parameters                     #
    #     ##################################
    #     # self.model.initial_soc = pyomo.Param(
    #     #     doc=self.block_set_name + " initial state-of-charge at beginning of the horizon[-]",
    #     #     within=pyomo.PercentFraction,
    #     #     default=0.5,
    #     #     mutable=True,
    #     #     units=u.dimensionless,
    #     # )
    #     ##################################
    #     # Constraints                    #
    #     ##################################

    #     # Linking time periods together
    #     def storage_soc_linking_rule(m, t):
    #         if t == self.blocks.index_set().first():
    #             return self.blocks[t].soc0 == self.model.initial_soc
    #         return self.blocks[t].soc0 == self.blocks[t - 1].soc

    #     self.model.soc_linking = pyomo.Constraint(
    #         self.blocks.index_set(),
    #         doc=self.block_set_name + " state-of-charge block linking constraint",
    #         rule=storage_soc_linking_rule,
    #     )

    def update_time_series_parameters(self, start_time: int = 0):
        """Updates time series parameters.

        Args:
            start_time (int): The start time.

        """
        # TODO: provide more control; currently don't use `start_time`
        self.time_duration = [1.0] * len(self.blocks.index_set())

    def update_dispatch_initial_soc(self, initial_soc: float | None = None):
        """Updates dispatch initial state of charge (SOC).

        Args:
            initial_soc (float, optional): Initial state of charge. Defaults to None.

        """
        if initial_soc is not None:
            self._system_model.value("initial_SOC", initial_soc)
            self._system_model.setup()  # TODO: Do I need to re-setup stateful battery?
        self.initial_soc = self._system_model.value("SOC")

    def set_fixed_dispatch(
        self,
        resource_in: list,
        max_charge_rate: list,
        max_discharge_rate: list,
    ):
        """Sets charge and discharge amount of storage dispatch using fixed_dispatch attribute
            and enforces available generation and charge/discharge limits.

        Args:
            resource_in (list): Resource blocks.
            max_charge_rate (list): Max charge capacity.
            max_discharge_rate (list): Max discharge capacity.

        Raises:
            ValueError: If resource_in or max_charge_rate or max_discharge_rate length does not
                match fixed_dispatch length.

        """
        self.check_resource_in_discharge_limit(resource_in, max_charge_rate, max_discharge_rate)
        self._set_resource_fraction_limits(resource_in, max_charge_rate, max_discharge_rate)
        self._heuristic_method(resource_in)
        self._fix_dispatch_model_variables()

    def check_resource_in_discharge_limit(
        self, resource_in: list, max_charge_rate: list, max_discharge_rate: list
    ):
        """Checks if resource in and discharge limit lengths match fixed_dispatch length.

        Args:
            resource_in (list): Resource blocks.
            max_charge_rate (list): Maximum charge capacity.
            max_discharge_rate (list): Maximum discharge capacity.

        Raises:
            ValueError: If gen or max_discharge_rate length does not match fixed_dispatch length.

        """
        if len(resource_in) != len(self.fixed_dispatch):
            raise ValueError("gen must be the same length as fixed_dispatch.")
        elif len(max_charge_rate) != len(self.fixed_dispatch):
            raise ValueError("max_charge_rate must be the same length as fixed_dispatch.")
        elif len(max_discharge_rate) != len(self.fixed_dispatch):
            raise ValueError("max_discharge_rate must be the same length as fixed_dispatch.")

    def _set_resource_fraction_limits(
        self, resource_in: list, max_charge_rate: list, max_discharge_rate: list
    ):
        """Set storage charge and discharge fraction limits based on
        available generation and grid capacity, respectively.

        Args:
            resource_in (list): Resource blocks.
            max_charge_rate (list): Maximum charge capacity.
            max_discharge_rate (list): Maximum discharge capacity.

        NOTE: This method assumes that storage cannot be charged by the grid.

        """
        for t in self.blocks.index_set():
            self.max_charge_fraction[t] = self.enforce_power_fraction_simple_bounds(
                (max_charge_rate[t] - resource_in[t]) / self.maximum_storage
            )
            self.max_discharge_fraction[t] = self.enforce_power_fraction_simple_bounds(
                (max_discharge_rate[t] - resource_in[t]) / self.maximum_storage
            )

    @staticmethod
    def enforce_power_fraction_simple_bounds(storage_fraction: float) -> float:
        """Enforces simple bounds (0, .9) for battery power fractions.

        Args:
            storage_fraction (float): Storage fraction from heuristic method.

        Returns:
            storage_fraction (float): Bounded storage fraction.

        """
        if storage_fraction > 0.9:
            storage_fraction = 0.9
        elif storage_fraction < 0.0:
            storage_fraction = 0.0
        return storage_fraction

    def update_soc(self, storage_fraction: float, soc0: float) -> float:
        """Updates SOC based on storage fraction threshold (0.1).

        Args:
            storage_fraction (float): Storage fraction from heuristic method. Below threshold
                is charging, above is discharging.
            soc0 (float): Initial SOC.

        Returns:
            soc (float): Updated SOC.

        """
        if storage_fraction > 0.0:
            discharge_resource = storage_fraction * self.maximum_storage
            soc = (
                soc0
                - self.time_duration[0]
                * (1 / (self.discharge_efficiency) * discharge_resource)
                / self.maximum_storage
            )
        elif storage_fraction < 0.0:
            charge_resource = -storage_fraction * self.maximum_storage
            soc = (
                soc0
                + self.time_duration[0]
                * (self.charge_efficiency * charge_resource)
                / self.maximum_storage
            )
        else:
            soc = soc0

        return max(self.minimum_soc, min(self.maximum_soc, soc))

    def _heuristic_method(self, _):
        """Executes specific heuristic method to fix storage dispatch."""
        self._enforce_power_fraction_limits()

    def _enforce_power_fraction_limits(self):
        """Enforces storage fraction limits and sets _fixed_dispatch attribute."""
        for t in self.blocks.index_set():
            fd = self.user_fixed_dispatch[t]
            if fd > 0.0:  # Discharging
                if fd > self.max_discharge_fraction[t]:
                    fd = self.max_discharge_fraction[t]
            elif fd < 0.0:  # Charging
                if -fd > self.max_charge_fraction[t]:
                    fd = -self.max_charge_fraction[t]
            self._fixed_dispatch[t] = fd

    def _fix_dispatch_model_variables(self):
        """Fixes dispatch model variables based on the fixed dispatch values."""
        soc0 = self.pyomo_model.initial_soc
        for t in self.blocks.index_set():
            dispatch_factor = self._fixed_dispatch[t]
            self.blocks[t].soc.fix(self.update_soc(dispatch_factor, soc0))
            soc0 = self.blocks[t].soc.value

            if dispatch_factor == 0.0:
                # Do nothing
                self.blocks[t].charge_resource.fix(0.0)
                self.blocks[t].discharge_resource.fix(0.0)
            elif dispatch_factor > 0.0:
                # Discharging
                self.blocks[t].charge_resource.fix(0.0)
                self.blocks[t].discharge_resource.fix(dispatch_factor * self.maximum_storage)
            elif dispatch_factor < 0.0:
                # Charging
                self.blocks[t].discharge_resource.fix(0.0)
                self.blocks[t].charge_resource.fix(-dispatch_factor * self.maximum_storage)

    def _check_initial_soc(self, initial_soc):
        """Checks initial state-of-charge.

        Args:
            initial_soc: Initial state-of-charge value.

        Returns:
            float: Checked initial state-of-charge.

        """
        initial_soc = round(initial_soc, self.round_digits)
        if initial_soc > self.maximum_soc:
            print(
                "Warning: Storage dispatch was initialized with a state-of-charge greater than "
                "maximum value!"
            )
            print(f"Initial SOC = {initial_soc}")
            print("Initial SOC was set to maximum value.")
            initial_soc = self.maximum_soc
        elif initial_soc < self.minimum_soc:
            print(
                "Warning: Storage dispatch was initialized with a state-of-charge less than "
                "minimum value!"
            )
            print(f"Initial SOC = {initial_soc}")
            print("Initial SOC was set to minimum value.")
            initial_soc = self.minimum_soc
        return initial_soc

    @property
    def fixed_dispatch(self) -> list:
        """list: List of fixed dispatch."""
        return self._fixed_dispatch

    @property
    def user_fixed_dispatch(self) -> list:
        """list: List of user fixed dispatch."""
        return self._user_fixed_dispatch

    @user_fixed_dispatch.setter
    def user_fixed_dispatch(self, fixed_dispatch: list):
        # TODO: Annual dispatch array...
        if len(fixed_dispatch) != len(self.blocks.index_set()):
            raise ValueError("fixed_dispatch must be the same length as dispatch index set.")
        elif max(fixed_dispatch) > 1.0 or min(fixed_dispatch) < -1.0:
            raise ValueError("fixed_dispatch must be normalized values between -1 and 1.")
        else:
            self._user_fixed_dispatch = fixed_dispatch

    @property
    def storage_dispatch_commands(self) -> list:
        """
        Commanded dispatch including available resource at current time step that has not
        been used to charge the battery.
        """
        return [
            (self.blocks[t].discharge_resource.value - self.blocks[t].charge_resource.value)
            for t in self.blocks.index_set()
        ]

    # @property
    # def current(self) -> list:
    #     """Current."""
    #     return [0.0 for t in self.blocks.index_set()]

    # @property
    # def generation(self) -> list:
    #     """Generation."""
    #     return self.storage_dispatch_commands

    @property
    def soc(self) -> list:
        """State-of-charge."""
        return [self.blocks[t].soc.value for t in self.blocks.index_set()]

    @property
    def charge_resource(self) -> list:
        """Charge resource."""
        return [self.blocks[t].charge_resource.value for t in self.blocks.index_set()]

    @property
    def discharge_resource(self) -> list:
        """Discharge resource."""
        return [self.blocks[t].discharge_resource.value for t in self.blocks.index_set()]

    @property
    def initial_soc(self) -> float:
        """Initial state-of-charge."""
        return self.pyomo_model.initial_soc.value

    @initial_soc.setter
    def initial_soc(self, initial_soc: float):
        initial_soc = self._check_initial_soc(initial_soc)
        self.pyomo_model.initial_soc = round(initial_soc, self.round_digits)

    @property
    def minimum_soc(self) -> float:
        """Minimum state-of-charge."""
        for t in self.blocks.index_set():
            return self.blocks[t].minimum_soc.value

    @minimum_soc.setter
    def minimum_soc(self, minimum_soc: float):
        for t in self.blocks.index_set():
            self.blocks[t].minimum_soc = round(minimum_soc, self.round_digits)

    @property
    def maximum_soc(self) -> float:
        """Maximum state-of-charge."""
        for t in self.blocks.index_set():
            return self.blocks[t].maximum_soc.value

    @maximum_soc.setter
    def maximum_soc(self, maximum_soc: float):
        for t in self.blocks.index_set():
            self.blocks[t].maximum_soc = round(maximum_soc, self.round_digits)

    @property
    def charge_efficiency(self) -> float:
        """Charge efficiency."""
        for t in self.blocks.index_set():
            return self.blocks[t].charge_efficiency.value

    @charge_efficiency.setter
    def charge_efficiency(self, efficiency: float):
        efficiency = self._check_efficiency_value(efficiency)
        for t in self.blocks.index_set():
            self.blocks[t].charge_efficiency = round(efficiency, self.round_digits)

    @property
    def discharge_efficiency(self) -> float:
        """Discharge efficiency."""
        for t in self.blocks.index_set():
            return self.blocks[t].discharge_efficiency.value

    @discharge_efficiency.setter
    def discharge_efficiency(self, efficiency: float):
        efficiency = self._check_efficiency_value(efficiency)
        for t in self.blocks.index_set():
            self.blocks[t].discharge_efficiency = round(efficiency, self.round_digits)

    @property
    def round_trip_efficiency(self) -> float:
        """Round trip efficiency."""
        return self.charge_efficiency * self.discharge_efficiency

    @round_trip_efficiency.setter
    def round_trip_efficiency(self, round_trip_efficiency: float):
        round_trip_efficiency = self._check_efficiency_value(round_trip_efficiency)
        # Assumes equal charge and discharge efficiencies
        efficiency = round_trip_efficiency ** (1 / 2)
        self.charge_efficiency = efficiency
        self.discharge_efficiency = efficiency


@define
class HeuristicLoadFollowingControllerConfig(PyomoControllerBaseConfig):
    rated_commodity_capacity: int = field()
    max_discharge_rate: float = field(default=1e12)
    max_charge_rate: float = field(default=1e12)
    charge_efficiency: float = field(default=None)
    discharge_efficiency: float = field(default=None)
    include_lifecycle_count: bool = field(default=False)

    def __attrs_post_init__(self):
        # TODO: Is this the best way to handle scalar charge/discharge rates?
        if isinstance(self.max_charge_rate, (float, int)):
            self.max_charge_rate = [self.max_charge_rate] * self.n_control_window
        if isinstance(self.max_discharge_rate, (float, int)):
            self.max_discharge_rate = [self.max_discharge_rate] * self.n_control_window


class HeuristicLoadFollowingController(SimpleBatteryControllerHeuristic):
    """Operates the battery based on heuristic rules to meet the demand profile based power
        available from power generation profiles and power demand profile.

    Currently, enforces available generation and grid limit assuming no battery charging from grid.

    """

    def setup(self):
        """Initialize HeuristicLoadFollowingController.

        Args:
            pyomo_model (pyomo.ConcreteModel): Pyomo concrete model.
            index_set (pyomo.Set): Indexed set.
            system_model (PySAMBatteryModel.BatteryStateful): System model.
            fixed_dispatch (Optional[List], optional): List of normalized values [-1, 1]
                (Charging (-), Discharging (+)). Defaults to None.
            block_set_name (str, optional): Name of the block set. Defaults to
                'heuristic_load_following_battery'.
            control_options (Optional[dict], optional): Dispatch options. Defaults to None.

        """
        self.config = HeuristicLoadFollowingControllerConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        self.n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        super().setup()

        if self.config.charge_efficiency is not None:
            self.charge_efficiency = self.config.charge_efficiency
        if self.config.discharge_efficiency is not None:
            self.discharge_efficiency = self.config.discharge_efficiency

    def set_fixed_dispatch(
        self,
        resource_in: list,
        max_charge_rate: list,
        max_discharge_rate: list,
        resource_demand: list,
    ):
        """Sets charge and discharge power of battery dispatch using fixed_dispatch attribute
            and enforces available generation and charge/discharge limits.

        Args:
            resource_in (list): List of generated resource in.
            max_charge_rate (list): List of max charge rates.
            max_discharge_rate (list): List of max discharge rates.
            resource_demand (list): The demanded resource.

        """

        self.check_resource_in_discharge_limit(resource_in, max_charge_rate, max_discharge_rate)
        self._set_resource_fraction_limits(resource_in, max_charge_rate, max_discharge_rate)
        self._heuristic_method(resource_in, resource_demand)
        self._fix_dispatch_model_variables()

    def _heuristic_method(self, resource_in, goal_resource):
        """Enforces storage fraction limits and sets _fixed_dispatch attribute.
        Sets the _fixed_dispatch based on goal_resource and gen.

        Args:
            generated_resource: Resource generation profile.
            goal_resource: Goal amount of resource.

        """
        for t in self.blocks.index_set():
            fd = (goal_resource[t] - resource_in[t]) / self.maximum_storage
            if fd > 0.0:  # Discharging
                if fd > self.max_discharge_fraction[t]:
                    fd = self.max_discharge_fraction[t]
            elif fd < 0.0:  # Charging
                if -fd > self.max_charge_fraction[t]:
                    fd = -self.max_charge_fraction[t]
            self._fixed_dispatch[t] = fd
