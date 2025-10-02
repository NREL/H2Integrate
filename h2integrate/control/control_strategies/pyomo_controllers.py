from typing import TYPE_CHECKING

import numpy as np
import pyomo.environ as pyomo
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import range_val
from h2integrate.control.control_strategies.controller_baseclass import ControllerBaseClass


if TYPE_CHECKING:  # to avoid circular imports
    pass


@define
class PyomoControllerBaseConfig(BaseConfig):
    """
    Configuration data container for Pyomo-based storage / dispatch controllers.

    This class groups the fundamental parameters needed by derived controller
    implementations. Values are typically populated from the technology
    `tech_config.yaml` (merged under the "control" section).

    Attributes:
        max_capacity (float):
            Physical maximum stored commodity capacity (inventory, not a rate).
            Units correspond to the base commodity units (e.g., kg, MWh).
        max_charge_percent (float):
            Upper bound on state of charge expressed as a fraction in [0, 1].
            1.0 means the controller may fill to max_capacity.
        min_charge_percent (float):
            Lower bound on state of charge expressed as a fraction in [0, 1].
            0.0 allows full depletion; >0 reserves minimum inventory.
        init_charge_percent (float):
            Initial state of charge at simulation start as a fraction in [0, 1].
        n_control_window (int):
            Number of consecutive timesteps processed per control action
            (rolling control / dispatch window length).
        n_horizon_window (int):
            Number of timesteps considered for look ahead / optimization horizon.
            May be >= n_control_window (used by predictive strategies).
        commodity_name (str):
            Base name of the controlled commodity (e.g., "hydrogen", "electricity").
            Used to construct input/output variable names (e.g., f"{commodity_name}_in").
        commodity_storage_units (str):
            Units string for stored commodity rates (e.g., "kg/h", "MW").
            Used for unit annotations when creating model variables.
        tech_name (str):
            Technology identifier used to namespace Pyomo blocks / variables within
            the broader OpenMDAO model (e.g., "battery", "h2_storage").
    """

    max_capacity: float = field()
    max_charge_percent: float = field(validator=range_val(0, 1))
    min_charge_percent: float = field(validator=range_val(0, 1))
    init_charge_percent: float = field(validator=range_val(0, 1))
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
        self.tech_group_name = self.pathname.split(".")

        # create inputs for all pyomo object creation functions from all connected technologies
        self.dispatch_connections = self.options["plant_config"]["tech_to_dispatch_connections"]
        for connection in self.dispatch_connections:
            # get connection definition
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
            # get connection definition
            source_tech, intended_dispatch_tech = connection
            # only add connections to intended dispatch tech
            if any(intended_dispatch_tech in name for name in self.tech_group_name):
                # names are specified differently if connecting within the tech group vs
                # connecting from an external tech group. This facilitates OM connections
                if source_tech == intended_dispatch_tech:
                    dispatch_block_rule_function = discrete_inputs["dispatch_block_rule_function"]
                else:
                    dispatch_block_rule_function = discrete_inputs[
                        f"{'dispatch_block_rule_function'}_{source_tech}"
                    ]
                # create pyomo block and set attr
                blocks = pyomo.Block(index_set, rule=dispatch_block_rule_function)
                setattr(self.pyomo_model, source_tech, blocks)
            else:
                continue

        # define dispatch solver
        def pyomo_dispatch_solver(
            performance_model: callable,
            performance_model_kwargs,
            inputs,
        ):
            self.initialize_parameters()

            # initialize outputs
            unmet_demand = np.zeros(self.n_timesteps)
            storage_commodity_out = np.zeros(self.n_timesteps)
            total_commodity_out = np.zeros(self.n_timesteps)
            excess_commodity = np.zeros(self.n_timesteps)
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
                    # TODO: implement optimized solutions; pyomo_model may be needed.
                    # Add pyomo_model=self.pyomo_model as input to pyomo_dispatch_solver
                    # if needed in the future.

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
                    excess_commodity[j] = np.maximum(
                        0, storage_commodity_out[j] + commodity_in[j - t] - demand_in[j - t]
                    )

            return total_commodity_out, storage_commodity_out, unmet_demand, excess_commodity, soc

        return pyomo_dispatch_solver

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
        max_charge_rate (float): Maximum rate at which the commodity can be charged (in units
            per time step, e.g., "kg/time step").
        max_discharge_rate (float): Maximum rate at which the commodity can be discharged (in
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

        self.round_digits = 4

        self.max_charge_fraction = [0.0] * self.config.n_control_window
        self.max_discharge_fraction = [0.0] * self.config.n_control_window
        self._fixed_dispatch = [0.0] * self.config.n_control_window

    def initialize_parameters(self):
        """Initializes parameters."""

        self.minimum_storage = 0.0
        self.maximum_storage = self.config.max_capacity
        self.minimum_soc = self.config.min_charge_percent
        self.maximum_soc = self.config.max_charge_percent
        self.initial_soc = self.config.init_charge_percent

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
        commodity_in: list,
        max_charge_rate: list,
        max_discharge_rate: list,
    ):
        """Sets charge and discharge amount of storage dispatch using fixed_dispatch attribute
            and enforces available generation and charge/discharge limits.

        Args:
            commodity_in (list): commodity blocks.
            max_charge_rate (list): Max charge capacity.
            max_discharge_rate (list): Max discharge capacity.

        Raises:
            ValueError: If commodity_in or max_charge_rate or max_discharge_rate length does not
                match fixed_dispatch length.

        """
        self.check_commodity_in_discharge_limit(commodity_in, max_charge_rate, max_discharge_rate)
        self._set_commodity_fraction_limits(commodity_in, max_charge_rate, max_discharge_rate)
        self._heuristic_method(commodity_in)
        self._fix_dispatch_model_variables()

    def check_commodity_in_discharge_limit(
        self, commodity_in: list, max_charge_rate: list, max_discharge_rate: list
    ):
        """Checks if commodity in and discharge limit lengths match fixed_dispatch length.

        Args:
            commodity_in (list): commodity blocks.
            max_charge_rate (list): Maximum charge capacity.
            max_discharge_rate (list): Maximum discharge capacity.

        Raises:
            ValueError: If gen or max_discharge_rate length does not match fixed_dispatch length.

        """
        if len(commodity_in) != len(self.fixed_dispatch):
            raise ValueError("gen must be the same length as fixed_dispatch.")
        elif len(max_charge_rate) != len(self.fixed_dispatch):
            raise ValueError("max_charge_rate must be the same length as fixed_dispatch.")
        elif len(max_discharge_rate) != len(self.fixed_dispatch):
            raise ValueError("max_discharge_rate must be the same length as fixed_dispatch.")

    def _set_commodity_fraction_limits(
        self, commodity_in: list, max_charge_rate: list, max_discharge_rate: list
    ):
        """Set storage charge and discharge fraction limits based on
        available generation and grid capacity, respectively.

        Args:
            commodity_in (list): commodity blocks.
            max_charge_rate (list): Maximum charge capacity.
            max_discharge_rate (list): Maximum discharge capacity.

        NOTE: This method assumes that storage cannot be charged by the grid.

        """
        for t in self.blocks.index_set():
            self.max_charge_fraction[t] = self.enforce_power_fraction_simple_bounds(
                (max_charge_rate[t] - commodity_in[t]) / self.maximum_storage
            )
            self.max_discharge_fraction[t] = self.enforce_power_fraction_simple_bounds(
                (max_discharge_rate[t] - commodity_in[t]) / self.maximum_storage
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
            discharge_commodity = storage_fraction * self.maximum_storage
            soc = (
                soc0
                - self.time_duration[0]
                * (1 / (self.discharge_efficiency) * discharge_commodity)
                / self.maximum_storage
            )
        elif storage_fraction < 0.0:
            charge_commodity = -storage_fraction * self.maximum_storage
            soc = (
                soc0
                + self.time_duration[0]
                * (self.charge_efficiency * charge_commodity)
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
                self.blocks[t].charge_commodity.fix(0.0)
                self.blocks[t].discharge_commodity.fix(0.0)
            elif dispatch_factor > 0.0:
                # Discharging
                self.blocks[t].charge_commodity.fix(0.0)
                self.blocks[t].discharge_commodity.fix(dispatch_factor * self.maximum_storage)
            elif dispatch_factor < 0.0:
                # Charging
                self.blocks[t].discharge_commodity.fix(0.0)
                self.blocks[t].charge_commodity.fix(-dispatch_factor * self.maximum_storage)

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
        Commanded dispatch including available commodity at current time step that has not
        been used to charge the battery.
        """
        return [
            (self.blocks[t].discharge_commodity.value - self.blocks[t].charge_commodity.value)
            for t in self.blocks.index_set()
        ]

    @property
    def soc(self) -> list:
        """State-of-charge."""
        return [self.blocks[t].soc.value for t in self.blocks.index_set()]

    @property
    def charge_commodity(self) -> list:
        """Charge commodity."""
        return [self.blocks[t].charge_commodity.value for t in self.blocks.index_set()]

    @property
    def discharge_commodity(self) -> list:
        """Discharge commodity."""
        return [self.blocks[t].discharge_commodity.value for t in self.blocks.index_set()]

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
        commodity_in: list,
        max_charge_rate: list,
        max_discharge_rate: list,
        commodity_demand: list,
    ):
        """Sets charge and discharge power of battery dispatch using fixed_dispatch attribute
            and enforces available generation and charge/discharge limits.

        Args:
            commodity_in (list): List of generated commodity in.
            max_charge_rate (list): List of max charge rates.
            max_discharge_rate (list): List of max discharge rates.
            commodity_demand (list): The demanded commodity.

        """

        self.check_commodity_in_discharge_limit(commodity_in, max_charge_rate, max_discharge_rate)
        self._set_commodity_fraction_limits(commodity_in, max_charge_rate, max_discharge_rate)
        self._heuristic_method(commodity_in, commodity_demand)
        self._fix_dispatch_model_variables()

    def _heuristic_method(self, commodity_in, goal_commodity):
        """Enforces storage fraction limits and sets _fixed_dispatch attribute.
        Sets the _fixed_dispatch based on goal_commodity and gen.

        Args:
            generated_commodity: commodity generation profile.
            goal_commodity: Goal amount of commodity.

        """
        for t in self.blocks.index_set():
            fd = (goal_commodity[t] - commodity_in[t]) / self.maximum_storage
            if fd > 0.0:  # Discharging
                if fd > self.max_discharge_fraction[t]:
                    fd = self.max_discharge_fraction[t]
            elif fd < 0.0:  # Charging
                if -fd > self.max_charge_fraction[t]:
                    fd = -self.max_charge_fraction[t]
            self._fixed_dispatch[t] = fd
