from copy import deepcopy
from typing import Optional, List, Dict, Union, TYPE_CHECKING

import openmdao.api as om
import pyomo.environ as pyomo
import numpy as np
from pyomo.network import Port
from pyomo.environ import units as u
from attrs import field, define

import PySAM.BatteryStateful as BatteryStateful

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import range_val, range_val_or_none
if TYPE_CHECKING: # to avoid circular imports
    from h2integrate.controllers.dispatch_options import DispatchOptions


class ControllerBaseClass(om.ExplicitComponent):
    """
    Base class for open-loop controllers in the H2Integrate system.

    This class provides a template for implementing open-loop controllers. It defines the
    basic structure for inputs and outputs and requires subclasses to implement the `compute`
    method for specific control logic.

    Attributes:
        plant_config (dict): Configuration dictionary for the overall plant.
        tech_config (dict): Configuration dictionary for the specific technology being controlled.
    """

    def initialize(self):
        """
        Declare options for the component. See "Attributes" section in class doc strings for
        details.
        """

        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        """
        Define inputs and outputs for the component.

        This method must be implemented in subclasses to define the specific control I/O.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("This method should be implemented in a subclass.")

    def compute(self, inputs, outputs):
        """
        Perform computations for the component.

        This method must be implemented in subclasses to define the specific control logic.

        Args:
            inputs (dict): Dictionary of input values.
            outputs (dict): Dictionary of output values.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("This method should be implemented in a subclass.")


class PyomoControllerBaseClass(ControllerBaseClass):
    def setup(
            self,
            pyomo_model: pyomo.ConcreteModel,
            index_set: pyomo.Set,
            system_model,
            block_set_name: str = "dispatch",
    ):
        self.block_set_name = block_set_name
        self.round_digits = int(4)

        self._model = pyomo_model
        self._blocks = pyomo.Block(index_set, rule=self.dispatch_block_rule)
        setattr(self.model, self.block_set_name, self.blocks)

        self._system_model = system_model

    @staticmethod
    def dispatch_block_rule(block, t):
        raise NotImplemented(
            "This function must be overridden for specific dispatch model"
        )

    def initialize_parameters(self):
        raise NotImplemented(
            "This function must be overridden for specific dispatch model"
        )

    def update_time_series_parameters(self, start_time: int):
        raise NotImplemented(
            "This function must be overridden for specific dispatch model"
        )

    @staticmethod
    def _check_efficiency_value(efficiency):
        """Checks efficiency is between 0 and 1 or 0 and 100. Returns fractional value"""
        if efficiency < 0:
            raise ValueError("Efficiency value must greater than 0")
        elif efficiency > 1:
            efficiency /= 100
            if efficiency > 1:
                raise ValueError("Efficiency value must between 0 and 1 or 0 and 100")
        return efficiency

    @property
    def blocks(self) -> pyomo.Block:
        return self._blocks

    @property
    def model(self) -> pyomo.ConcreteModel:
        return self._model


class SimpleBatteryDispatchHeuristic(PyomoControllerBaseClass):
    """Fixes battery dispatch operations based on user input.

    Currently, enforces available generation and grid limit assuming no battery charging from grid.

    """

    def setup(
        self,
        pyomo_model: pyomo.ConcreteModel,
        index_set: pyomo.Set,
        system_model: BatteryStateful.BatteryStateful,
        fixed_dispatch: Optional[List] = None,
        block_set_name: str = "heuristic_battery",
        dispatch_options: Optional[Dict] = None,
    ):
        """Initialize SimpleBatteryDispatchHeuristic.

        Args:
            pyomo_model (pyomo.ConcreteModel): Pyomo concrete model.
            index_set (pyomo.Set): Indexed set.
            system_model (PySAMBatteryModel.BatteryStateful): Battery system model.
            fixed_dispatch (Optional[List], optional): List of normalized values [-1, 1] (Charging (-), Discharging (+)). Defaults to None.
            block_set_name (str, optional): Name of block set. Defaults to 'heuristic_battery'.
            dispatch_options (dict, optional): Dispatch options. Defaults to None.

        """
        if dispatch_options is None:
            dispatch_options = {}
        super().setup(
            pyomo_model,
            index_set,
            system_model,
            block_set_name=block_set_name,
        )

        self._create_soc_linking_constraint()

        # TODO: we could remove this option and just have lifecycle count default
        self.dispatch_options = dispatch_options
        if self.dispatch_options.include_lifecycle_count:
            self._create_lifecycle_model()
            if self.dispatch_options.max_lifecycle_per_day < np.inf:
                self._create_lifecycle_count_constraint()

        self.max_charge_fraction = list([0.0] * len(self.blocks.index_set()))
        self.max_discharge_fraction = list([0.0] * len(self.blocks.index_set()))
        self.user_fixed_dispatch = list([0.0] * len(self.blocks.index_set()))
        # TODO: should I enforce either a day schedule or a year schedule year and save it as user input.
        #  Additionally, Should I drop it as input in the init function?
        if fixed_dispatch is not None:
            self.user_fixed_dispatch = fixed_dispatch

        self._fixed_dispatch = list([0.0] * len(self.blocks.index_set()))

    def initialize_parameters(self):
        """Initializes parameters."""
        if self.config.include_lifecycle_count:
            self.lifecycle_cost = (
                self.options.lifecycle_cost_per_kWh_cycle
                * self._system_model.value("nominal_energy")
            )

        # self.cost_per_charge = self._financial_model.value("om_batt_variable_cost")[
        #     0
        # ]  # [$/MWh]
        # self.cost_per_discharge = self._financial_model.value("om_batt_variable_cost")[
        #     0
        # ]  # [$/MWh]
        self.minimum_power = 0.0
        # FIXME: Change C_rate call to user set system_capacity_kw
        # self.maximum_power = self._system_model.value('nominal_energy') * self._system_model.value('C_rate') / 1e3
        print(dir(self._system_model))
        self.maximum_power = self.config.system_capacity_kw
        self.minimum_soc = self._system_model.value("minimum_SOC")
        self.maximum_soc = self._system_model.value("maximum_SOC")
        self.initial_soc = self._system_model.value("initial_SOC")

        self._set_control_mode()
        self._set_model_specific_parameters()

    def dispatch_block_rule(self, storage):
        """Initializes storage parameters, variables, and constraints.
            Called during Dispatch's __init__.

        Args:
            storage: Storage instance.

        """
        # Parameters
        self._create_storage_parameters(storage)
        self._create_efficiency_parameters(storage)
        self._create_capacity_parameter(storage)
        # Variables
        self._create_storage_variables(storage)
        # Constraints
        self._create_storage_constraints(storage)
        self._create_soc_inventory_constraint(storage)
        # Ports
        self._create_storage_port(storage)

    def _create_storage_parameters(self, storage):
        """Creates storage parameters.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Parameters                     #
        ##################################
        storage.time_duration = pyomo.Param(
            doc="Time step [hour]",
            default=1.0,
            within=pyomo.NonNegativeReals,
            mutable=True,
            units=u.hr,
        )
        # storage.cost_per_charge = pyomo.Param(
        #     doc="Operating cost of " + self.block_set_name + " charging [$/MWh]",
        #     default=0.0,
        #     within=pyomo.NonNegativeReals,
        #     mutable=True,
        #     units=u.USD / u.MWh,
        # )
        # storage.cost_per_discharge = pyomo.Param(
        #     doc="Operating cost of " + self.block_set_name + " discharging [$/MWh]",
        #     default=0.0,
        #     within=pyomo.NonNegativeReals,
        #     mutable=True,
        #     units=u.USD / u.MWh,
        # )
        storage.minimum_power = pyomo.Param(
            doc=self.block_set_name + " minimum power rating [MW]",
            default=0.0,
            within=pyomo.NonNegativeReals,
            mutable=True,
            units=u.MW,
        )
        storage.maximum_power = pyomo.Param(
            doc=self.block_set_name + " maximum power rating [MW]",
            within=pyomo.NonNegativeReals,
            mutable=True,
            units=u.MW,
        )
        storage.minimum_soc = pyomo.Param(
            doc=self.block_set_name + " minimum state-of-charge [-]",
            default=0.1,
            within=pyomo.PercentFraction,
            mutable=True,
            units=u.dimensionless,
        )
        storage.maximum_soc = pyomo.Param(
            doc=self.block_set_name + " maximum state-of-charge [-]",
            default=0.9,
            within=pyomo.PercentFraction,
            mutable=True,
            units=u.dimensionless,
        )

    def _create_efficiency_parameters(self, storage):
        """Creates storage efficiency parameters.

        Args:
            storage: Storage instance.

        """
        storage.charge_efficiency = pyomo.Param(
            doc=self.block_set_name + " Charging efficiency [-]",
            default=0.938,
            within=pyomo.PercentFraction,
            mutable=True,
            units=u.dimensionless,
        )
        storage.discharge_efficiency = pyomo.Param(
            doc=self.block_set_name + " discharging efficiency [-]",
            default=0.938,
            within=pyomo.PercentFraction,
            mutable=True,
            units=u.dimensionless,
        )

    def _create_capacity_parameter(self, storage):
        """Creates storage capacity parameter.

        Args:
            storage: Storage instance.

        """
        storage.capacity = pyomo.Param(
            doc=self.block_set_name + " capacity [MWh]",
            within=pyomo.NonNegativeReals,
            mutable=True,
            units=u.MWh,
        )

    def _create_storage_variables(self, storage):
        """Creates storage variables.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Variables                      #
        ##################################
        storage.is_charging = pyomo.Var(
            doc="1 if " + self.block_set_name + " is charging; 0 Otherwise [-]",
            domain=pyomo.Binary,
            units=u.dimensionless,
        )
        storage.is_discharging = pyomo.Var(
            doc="1 if " + self.block_set_name + " is discharging; 0 Otherwise [-]",
            domain=pyomo.Binary,
            units=u.dimensionless,
        )
        storage.soc0 = pyomo.Var(
            doc=self.block_set_name
            + " initial state-of-charge at beginning of period[-]",
            domain=pyomo.PercentFraction,
            bounds=(storage.minimum_soc, storage.maximum_soc),
            units=u.dimensionless,
        )
        storage.soc = pyomo.Var(
            doc=self.block_set_name + " state-of-charge at end of period [-]",
            domain=pyomo.PercentFraction,
            bounds=(storage.minimum_soc, storage.maximum_soc),
            units=u.dimensionless,
        )
        storage.charge_power = pyomo.Var(
            doc="Power into " + self.block_set_name + " [MW]",
            domain=pyomo.NonNegativeReals,
            units=u.MW,
        )
        storage.discharge_power = pyomo.Var(
            doc="Power out of " + self.block_set_name + " [MW]",
            domain=pyomo.NonNegativeReals,
            units=u.MW,
        )

    def _create_storage_constraints(self, storage):
        ##################################
        # Constraints                    #
        ##################################
        # Charge power bounds
        storage.charge_power_ub = pyomo.Constraint(
            doc=self.block_set_name + " charging power upper bound",
            expr=storage.charge_power <= storage.maximum_power * storage.is_charging,
        )
        storage.charge_power_lb = pyomo.Constraint(
            doc=self.block_set_name + " charging power lower bound",
            expr=storage.charge_power >= storage.minimum_power * storage.is_charging,
        )
        # Discharge power bounds
        storage.discharge_power_lb = pyomo.Constraint(
            doc=self.block_set_name + " Discharging power lower bound",
            expr=storage.discharge_power
            >= storage.minimum_power * storage.is_discharging,
        )
        storage.discharge_power_ub = pyomo.Constraint(
            doc=self.block_set_name + " Discharging power upper bound",
            expr=storage.discharge_power
            <= storage.maximum_power * storage.is_discharging,
        )
        # Storage packing constraint
        storage.charge_discharge_packing = pyomo.Constraint(
            doc=self.block_set_name
            + " packing constraint for charging and discharging binaries",
            expr=storage.is_charging + storage.is_discharging <= 1,
        )

    def _create_soc_inventory_constraint(self, storage):
        """Creates state-of-charge inventory constraint for storage.

        Args:
            storage: Storage instance.

        """

        def soc_inventory_rule(m):
            return m.soc == (
                m.soc0
                + m.time_duration
                * (
                    m.charge_efficiency * m.charge_power
                    - (1 / m.discharge_efficiency) * m.discharge_power
                )
                / m.capacity
            )

        # Storage State-of-charge balance
        storage.soc_inventory = pyomo.Constraint(
            doc=self.block_set_name + " state-of-charge inventory balance",
            rule=soc_inventory_rule,
        )

    @staticmethod
    def _create_storage_port(storage):
        """Creates storage port.

        Args:
            storage: Storage instance.

        """
        ##################################
        # Ports                          #
        ##################################
        storage.port = Port()
        storage.port.add(storage.charge_power)
        storage.port.add(storage.discharge_power)

    def _set_control_mode(self):
        """Sets control mode."""
        if isinstance(self._system_model, BatteryStateful.BatteryStateful):
            self._system_model.value("control_mode", 1.0)  # Power control
            self._system_model.value("input_power", 0.0)
            self.control_variable = "input_power"

    def _set_model_specific_parameters(self, round_trip_efficiency=88.0):
        """Sets model-specific parameters.

        Args:
            round_trip_efficiency (float, optional): The round-trip efficiency including converter efficiency.
                Defaults to 88.0, which includes converter efficiency.

        """
        self.round_trip_efficiency = (
            round_trip_efficiency  # Including converter efficiency
        )
        self.capacity = self._system_model.value("nominal_energy") / 1e3  # [MWh]

    def _create_soc_linking_constraint(self):
        """Creates state-of-charge linking constraint."""
        ##################################
        # Parameters                     #
        ##################################
        self.model.initial_soc = pyomo.Param(
            doc=self.block_set_name
            + " initial state-of-charge at beginning of the horizon[-]",
            within=pyomo.PercentFraction,
            default=0.5,
            mutable=True,
            units=u.dimensionless,
        )
        ##################################
        # Constraints                    #
        ##################################

        # Linking time periods together
        def storage_soc_linking_rule(m, t):
            if t == self.blocks.index_set().first():
                return self.blocks[t].soc0 == self.model.initial_soc
            return self.blocks[t].soc0 == self.blocks[t - 1].soc

        self.model.soc_linking = pyomo.Constraint(
            self.blocks.index_set(),
            doc=self.block_set_name + " state-of-charge block linking constraint",
            rule=storage_soc_linking_rule,
        )

    def update_time_series_parameters(self, start_time: int):
        """Updates time series parameters.

        Args:
            start_time (int): The start time.

        """
        # TODO: provide more control
        self.time_duration = [1.0] * len(self.blocks.index_set())

    def update_dispatch_initial_soc(self, initial_soc: float = None):
        """Updates dispatch initial state of charge (SOC).

        Args:
            initial_soc (float, optional): Initial state of charge. Defaults to None.

        """
        if initial_soc is not None:
            self._system_model.value("initial_SOC", initial_soc)
            self._system_model.setup()  # TODO: Do I need to re-setup stateful battery?
        self.initial_soc = self._system_model.value("SOC")

    def set_fixed_dispatch(self, gen: list, grid_limit: list):
        """Sets charge and discharge power of battery dispatch using fixed_dispatch attribute and enforces available
        generation and grid limits.

        Args:
            gen (list): Generation blocks.
            grid_limit (list): Grid capacity.

        Raises:
            ValueError: If gen or grid_limit length does not match fixed_dispatch length.

        """
        self.check_gen_grid_limit(gen, grid_limit)
        self._set_power_fraction_limits(gen, grid_limit)
        self._heuristic_method(gen)
        self._fix_dispatch_model_variables()

    def check_gen_grid_limit(self, gen: list, grid_limit: list):
        """Checks if generation and grid limit lengths match fixed_dispatch length.

        Args:
            gen (list): Generation blocks.
            grid_limit (list): Grid capacity.

        Raises:
            ValueError: If gen or grid_limit length does not match fixed_dispatch length.

        """
        if len(gen) != len(self.fixed_dispatch):
            raise ValueError("gen must be the same length as fixed_dispatch.")
        elif len(grid_limit) != len(self.fixed_dispatch):
            raise ValueError("grid_limit must be the same length as fixed_dispatch.")

    def _set_power_fraction_limits(self, gen: list, grid_limit: list):
        """Set battery charge and discharge power fraction limits based on
        available generation and grid capacity, respectively.

        Args:
            gen (list): Generation blocks.
            grid_limit (list): Grid capacity.

        NOTE: This method assumes that battery cannot be charged by the grid.

        """
        for t in self.blocks.index_set():
            self.max_charge_fraction[t] = self.enforce_power_fraction_simple_bounds(
                gen[t] / self.maximum_power
            )
            self.max_discharge_fraction[t] = self.enforce_power_fraction_simple_bounds(
                (grid_limit[t] - gen[t]) / self.maximum_power
            )

    @staticmethod
    def enforce_power_fraction_simple_bounds(power_fraction: float) -> float:
        """Enforces simple bounds (0, .9) for battery power fractions.

        Args:
            power_fraction (float): Power fraction from heuristic method.

        Returns:
            power_fraction (float): Bounded power fraction.

        """
        if power_fraction > 0.9:
            power_fraction = 0.9
        elif power_fraction < 0.0:
            power_fraction = 0.0
        return power_fraction

    def update_soc(self, power_fraction: float, soc0: float) -> float:
        """Updates SOC based on power fraction threshold (0.1).

        Args:
            power_fraction (float): Power fraction from heuristic method. Below threshold
                is charging, above is discharging.
            soc0 (float): Initial SOC.

        Returns:
            soc (float): Updated SOC.
            
        """
        if power_fraction > 0.0:
            discharge_power = power_fraction * self.maximum_power
            soc = (
                soc0
                - self.time_duration[0]
                * (1 / (self.discharge_efficiency / 100.0) * discharge_power)
                / self.capacity
            )
        elif power_fraction < 0.0:
            charge_power = -power_fraction * self.maximum_power
            soc = (
                soc0
                + self.time_duration[0]
                * (self.charge_efficiency / 100.0 * charge_power)
                / self.capacity
            )
        else:
            soc = soc0

        min_soc = self._system_model.value("minimum_SOC") / 100
        max_soc = self._system_model.value("maximum_SOC") / 100

        soc = max(min_soc, min(max_soc, soc))

        return soc

    def _heuristic_method(self, _):
        """Executes specific heuristic method to fix battery dispatch."""
        self._enforce_power_fraction_limits()

    def _enforce_power_fraction_limits(self):
        """Enforces battery power fraction limits and sets _fixed_dispatch attribute."""
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
        soc0 = self.model.initial_soc.value
        for t in self.blocks.index_set():
            dispatch_factor = self._fixed_dispatch[t]
            self.blocks[t].soc.fix(self.update_soc(dispatch_factor, soc0))
            soc0 = self.blocks[t].soc.value

            if dispatch_factor == 0.0:
                # Do nothing
                self.blocks[t].charge_power.fix(0.0)
                self.blocks[t].discharge_power.fix(0.0)
            elif dispatch_factor > 0.0:
                # Discharging
                self.blocks[t].charge_power.fix(0.0)
                self.blocks[t].discharge_power.fix(dispatch_factor * self.maximum_power)
            elif dispatch_factor < 0.0:
                # Charging
                self.blocks[t].discharge_power.fix(0.0)
                self.blocks[t].charge_power.fix(-dispatch_factor * self.maximum_power)

    def _check_initial_soc(self, initial_soc):
        """Checks initial state-of-charge.

        Args:
            initial_soc: Initial state-of-charge value.

        Returns:
            float: Checked initial state-of-charge.
            
        """
        if initial_soc > 1:
            initial_soc /= 100.0
        initial_soc = round(initial_soc, self.round_digits)
        if initial_soc > self.maximum_soc / 100:
            print(
                "Warning: Storage dispatch was initialized with a state-of-charge greater than "
                "maximum value!"
            )
            print("Initial SOC = {}".format(initial_soc))
            print("Initial SOC was set to maximum value.")
            initial_soc = self.maximum_soc / 100
        elif initial_soc < self.minimum_soc / 100:
            print(
                "Warning: Storage dispatch was initialized with a state-of-charge less than "
                "minimum value!"
            )
            print("Initial SOC = {}".format(initial_soc))
            print("Initial SOC was set to minimum value.")
            initial_soc = self.minimum_soc / 100
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
            raise ValueError(
                "fixed_dispatch must be the same length as dispatch index set."
            )
        elif max(fixed_dispatch) > 1.0 or min(fixed_dispatch) < -1.0:
            raise ValueError(
                "fixed_dispatch must be normalized values between -1 and 1."
            )
        else:
            self._user_fixed_dispatch = fixed_dispatch

    @property
    def power(self) -> list:
        """Power."""
        return [
            self.blocks[t].discharge_power.value - self.blocks[t].charge_power.value
            for t in self.blocks.index_set()
        ]

    @property
    def current(self) -> list:
        """Current."""
        return [0.0 for t in self.blocks.index_set()]

    @property
    def generation(self) -> list:
        """Generation."""
        return self.power

    @property
    def soc(self) -> list:
        """State-of-charge."""
        return [self.blocks[t].soc.value * 100.0 for t in self.blocks.index_set()]

    @property
    def charge_power(self) -> list:
        """Charge power."""
        return [self.blocks[t].charge_power.value for t in self.blocks.index_set()]

    @property
    def discharge_power(self) -> list:
        """Discharge power."""
        return [self.blocks[t].discharge_power.value for t in self.blocks.index_set()]

    @property
    def initial_soc(self) -> float:
        """Initial state-of-charge."""
        return self.model.initial_soc.value * 100.0

    @initial_soc.setter
    def initial_soc(self, initial_soc: float):
        initial_soc = self._check_initial_soc(initial_soc)
        self.model.initial_soc = round(initial_soc, self.round_digits)

    @property
    def minimum_soc(self) -> float:
        """Minimum state-of-charge."""
        for t in self.blocks.index_set():
            return self.blocks[t].minimum_soc.value * 100.0

    @minimum_soc.setter
    def minimum_soc(self, minimum_soc: float):
        if minimum_soc > 1:
            minimum_soc /= 100.0
        for t in self.blocks.index_set():
            self.blocks[t].minimum_soc = round(minimum_soc, self.round_digits)

    @property
    def maximum_soc(self) -> float:
        """Maximum state-of-charge."""
        for t in self.blocks.index_set():
            return self.blocks[t].maximum_soc.value * 100.0

    @maximum_soc.setter
    def maximum_soc(self, maximum_soc: float):
        if maximum_soc > 1:
            maximum_soc /= 100.0
        for t in self.blocks.index_set():
            self.blocks[t].maximum_soc = round(maximum_soc, self.round_digits)

    @property
    def charge_efficiency(self) -> float:
        """Charge efficiency."""
        for t in self.blocks.index_set():
            return self.blocks[t].charge_efficiency.value * 100.0

    @charge_efficiency.setter
    def charge_efficiency(self, efficiency: float):
        efficiency = self._check_efficiency_value(efficiency)
        for t in self.blocks.index_set():
            self.blocks[t].charge_efficiency = round(efficiency, self.round_digits)

    @property
    def discharge_efficiency(self) -> float:
        """Discharge efficiency."""
        for t in self.blocks.index_set():
            return self.blocks[t].discharge_efficiency.value * 100.0

    @discharge_efficiency.setter
    def discharge_efficiency(self, efficiency: float):
        efficiency = self._check_efficiency_value(efficiency)
        for t in self.blocks.index_set():
            self.blocks[t].discharge_efficiency = round(efficiency, self.round_digits)


@define
class HeuristicLoadFollowingDispatchConfig(BaseConfig):
    resource_name: str = field()
    resource_units: str = field()
    system_capacity_kw: int = field()
    include_lifecycle_count: bool = field(default=False)


class HeuristicLoadFollowingDispatch(SimpleBatteryDispatchHeuristic):
    """Operates the battery based on heuristic rules to meet the demand profile based power available from power generation profiles and
        power demand profile.

    Currently, enforces available generation and grid limit assuming no battery charging from grid

    """

    def setup(
        self,
        pyomo_model: pyomo.ConcreteModel,
        index_set: pyomo.Set,
        system_model: BatteryStateful.BatteryStateful,
        fixed_dispatch: Optional[List] = None,
        block_set_name: str = "heuristic_load_following_battery",
        dispatch_options: Optional[Union[Dict, 'DispatchOptions']] = None,
    ):
        """Initialize HeuristicLoadFollowingDispatch.

        Args:
            pyomo_model (pyomo.ConcreteModel): Pyomo concrete model.
            index_set (pyomo.Set): Indexed set.
            system_model (PySAMBatteryModel.BatteryStateful): System model.
            fixed_dispatch (Optional[List], optional): List of normalized values [-1, 1] (Charging (-), Discharging (+)). Defaults to None.
            block_set_name (str, optional): Name of the block set. Defaults to 'heuristic_load_following_battery'.
            dispatch_options (Optional[dict], optional): Dispatch options. Defaults to None.

        """
        super().setup(
            pyomo_model,
            index_set,
            system_model,
            fixed_dispatch,
            block_set_name,
            dispatch_options,
        )

        self.config = HeuristicLoadFollowingDispatchConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

    def set_fixed_dispatch(self, gen: list, grid_limit: list, goal_power: list):
        """Sets charge and discharge power of battery dispatch using fixed_dispatch attribute
            and enforces available generation and grid limits.

        Args:
            gen (list): List of power generation.
            grid_limit (list): List of grid limits.
            goal_power (list): List of goal power.

        """

        self.check_gen_grid_limit(gen, grid_limit)
        self._set_power_fraction_limits(gen, grid_limit)
        self._heuristic_method(gen, goal_power)
        self._fix_dispatch_model_variables()

    def _heuristic_method(self, gen, goal_power):
        """Enforces battery power fraction limits and sets _fixed_dispatch attribute.
        Sets the _fixed_dispatch based on goal_power and gen (power generation profile).

        Args:
            gen: Power generation profile.
            goal_power: Goal power.

        """
        for t in self.blocks.index_set():
            fd = (goal_power[t] - gen[t]) / self.maximum_power
            if fd > 0.0:  # Discharging
                if fd > self.max_discharge_fraction[t]:
                    fd = self.max_discharge_fraction[t]
            elif fd < 0.0:  # Charging
                if -fd > self.max_charge_fraction[t]:
                    fd = -self.max_charge_fraction[t]
            self._fixed_dispatch[t] = fd


@define
class PassThroughOpenLoopControllerConfig(BaseConfig):
    resource_name: str = field()
    resource_rate_units: str = field()


class PassThroughOpenLoopController(ControllerBaseClass):
    """
    A simple pass-through controller for open-loop systems.

    This controller directly passes the input resource flow to the output without any
    modifications. It is useful for testing, as a placeholder for more complex controllers,
    and for maintaining consistency between controlled and uncontrolled frameworks as this
    'controller' does not alter the system output in any way.
    """

    def setup(self):
        self.config = PassThroughOpenLoopControllerConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        self.add_input(
            f"{self.config.resource_name}_in",
            shape_by_conn=True,
            units=self.config.resource_rate_units,
            desc=f"{self.config.resource_name} input timeseries from production to storage",
        )

        self.add_output(
            f"{self.config.resource_name}_out",
            copy_shape=f"{self.config.resource_name}_in",
            units=self.config.resource_rate_units,
            desc=f"{self.config.resource_name} output timeseries from plant after storage",
        )

    def compute(self, inputs, outputs):
        """
        Pass through input to output flows.

        Args:
            inputs (dict): Dictionary of input values.
                - {resource_name}_in: Input resource flow.
            outputs (dict): Dictionary of output values.
                - {resource_name}_out: Output resource flow, equal to the input flow.
        """

        # Assign the input to the output
        outputs[f"{self.config.resource_name}_out"] = inputs[f"{self.config.resource_name}_in"]

    def setup_partials(self):
        """
        Declare partial derivatives as unity throughout the design space.

        This method specifies that the derivative of the output with respect to the input is
        always 1.0, consistent with the pass-through behavior.

        Note:
        This method is not currently used and isn't strictly needed if you're creating other
        controllers; it is included as a nod towards potential future development enabling
        more derivative information passing.
        """

        # Get the size of the input/output array
        size = self._get_var_meta(f"{self.config.resource_name}_in", "size")

        # Declare partials sparsely for all elements as an identity matrix
        # (diagonal elements are 1.0, others are 0.0)
        self.declare_partials(
            of=f"{self.config.resource_name}_out",
            wrt=f"{self.config.resource_name}_in",
            rows=np.arange(size),
            cols=np.arange(size),
            val=np.ones(size),  # Diagonal elements are 1.0
        )


@define
class DemandOpenLoopControllerConfig(BaseConfig):
    """
    Configuration class for the DemandOpenLoopController.

    This class defines the parameters required to configure the `DemandOpenLoopController`.

    Attributes:
        resource_name (str): Name of the resource being controlled (e.g., "hydrogen").
        resource_rate_units (str): Units of the resource (e.g., "kg/h").
        max_capacity (float): Maximum storage capacity of the resource (in non-rate units,
            e.g., "kg" if `resource_rate_units` is "kg/h").
        max_charge_percent (float): Maximum allowable state of charge (SOC) as a percentage
            of `max_capacity`, represented as a decimal between 0 and 1.
        min_charge_percent (float): Minimum allowable SOC as a percentage of `max_capacity`,
            represented as a decimal between 0 and 1.
        init_charge_percent (float): Initial SOC as a percentage of `max_capacity`, represented
            as a decimal between 0 and 1.
        max_charge_rate (float): Maximum rate at which the resource can be charged (in units
            per time step, e.g., "kg/time step"). This rate does not include the charge_efficiency.
        max_discharge_rate (float): Maximum rate at which the resource can be discharged (in
            units per time step, e.g., "kg/time step"). This rate does not include the
            discharge_efficiency.
        charge_efficiency (float | None): Efficiency of charging the storage, represented as a
            decimal between 0 and 1 (e.g., 0.9 for 90% efficiency). Optional if
            `round_trip_efficiency` is provided.
        discharge_efficiency (float | None): Efficiency of discharging the storage, represented
            as a decimal between 0 and 1 (e.g., 0.9 for 90% efficiency). Optional if
            `round_trip_efficiency` is provided.
        round_trip_efficiency (float | None): Combined efficiency of charging and discharging
            the storage, represented as a decimal between 0 and 1 (e.g., 0.81 for 81% efficiency).
            Optional if `charge_efficiency` and `discharge_efficiency` are provided.
        demand_profile (scalar or list): The demand values for each time step (in the same units
            as `resource_rate_units`) or a scalar for a constant demand.
        n_time_steps (int): Number of time steps in the simulation. Defaults to 8760.
    """

    resource_name: str = field()
    resource_rate_units: str = field()
    max_capacity: float = field()
    max_charge_percent: float = field(validator=range_val(0, 1))
    min_charge_percent: float = field(validator=range_val(0, 1))
    init_charge_percent: float = field(validator=range_val(0, 1))
    max_charge_rate: float = field()
    max_discharge_rate: float = field()
    demand_profile: int | float | list = field()
    n_time_steps: int = field(default=8760)
    charge_efficiency: float | None = field(default=None, validator=range_val_or_none(0, 1))
    discharge_efficiency: float | None = field(default=None, validator=range_val_or_none(0, 1))
    round_trip_efficiency: float | None = field(default=None, validator=range_val_or_none(0, 1))

    def __attrs_post_init__(self):
        """
        Post-initialization logic to validate and calculate efficiencies.

        Ensures that either `charge_efficiency` and `discharge_efficiency` are provided,
        or `round_trip_efficiency` is provided. If `round_trip_efficiency` is provided,
        it calculates `charge_efficiency` and `discharge_efficiency` as the square root
        of `round_trip_efficiency`.
        """
        if self.round_trip_efficiency is not None:
            if self.charge_efficiency is not None or self.discharge_efficiency is not None:
                raise ValueError(
                    "Provide either `round_trip_efficiency` or both `charge_efficiency` "
                    "and `discharge_efficiency`, but not both."
                )
            # Calculate charge and discharge efficiencies from round-trip efficiency
            self.charge_efficiency = np.sqrt(self.round_trip_efficiency)
            self.discharge_efficiency = np.sqrt(self.round_trip_efficiency)
        elif self.charge_efficiency is not None and self.discharge_efficiency is not None:
            # Ensure both charge and discharge efficiencies are provided
            pass
        else:
            raise ValueError(
                "You must provide either `round_trip_efficiency` or both "
                "`charge_efficiency` and `discharge_efficiency`."
            )


class DemandOpenLoopController(ControllerBaseClass):
    """
    A controller that manages resource flow based on demand and storage constraints.

    The `DemandOpenLoopController` computes the state of charge (SOC), output flow, curtailment,
    and missed load for a resource storage system. It uses a demand profile and storage parameters
    to determine how much of the resource to charge, discharge, or curtail at each time step.

    Note: the units of the outputs are the same as the resource units, which is typically a rate
    in H2Integrate (e.g. kg/h)

    Attributes:
        config (DemandOpenLoopControllerConfig): Configuration object containing parameters
            such as resource name, units, time steps, storage capacity, charge/discharge rates,
            efficiencies, and demand profile.

    Inputs:
        {resource_name}_in (float): Input resource flow timeseries (e.g., hydrogen production).
            - Units: Defined in `resource_rate_units` (e.g., "kg/h").

    Outputs:
        {resource_name}_out (float): Output resource flow timeseries after storage.
            - Units: Defined in `resource_rate_units` (e.g., "kg/h").
        {resource_name}_soc (float): State of charge (SOC) timeseries for the storage system.
            - Units: "unitless" (percentage of maximum capacity given as a ratio between 0 and 1).
        {resource_name}_curtailed (float): Curtailment timeseries for unused input resource.
            - Units: Defined in `resource_rate_units` (e.g., "kg/h").
            - Note: curtailment in this case does not reduce what the converter produces, but
                rather the system just does not use it (throws it away) because this controller is
                specific to the storage technology and has no influence on other technologies in
                the system.
        {resource_name}_missed_load (float): Missed load timeseries when demand exceeds supply.
            - Units: Defined in `resource_rate_units` (e.g., "kg/h").

    """

    def setup(self):
        self.config = DemandOpenLoopControllerConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        resource_name = self.config.resource_name

        self.add_input(
            f"{resource_name}_in",
            shape_by_conn=True,
            units=self.config.resource_rate_units,
            desc=f"{resource_name} input timeseries from production to storage",
        )

        if isinstance(self.config.demand_profile, int | float):
            self.config.demand_profile = [self.config.demand_profile] * self.config.n_time_steps

        self.add_input(
            f"{resource_name}_demand_profile",
            units=f"{self.config.resource_rate_units}/h",
            val=self.config.demand_profile,
            shape=self.config.n_time_steps,
            desc=f"{resource_name} demand profile timeseries",
        )

        self.add_output(
            f"{resource_name}_out",
            copy_shape=f"{resource_name}_in",
            units=self.config.resource_rate_units,
            desc=f"{resource_name} output timeseries from plant after storage",
        )

        self.add_output(
            f"{resource_name}_soc",
            copy_shape=f"{resource_name}_in",
            units="unitless",
            desc=f"{resource_name} state of charge timeseries for storage",
        )

        self.add_output(
            f"{resource_name}_curtailed",
            copy_shape=f"{resource_name}_in",
            units=self.config.resource_rate_units,
            desc=f"{resource_name} curtailment timeseries for inflow resource at \
                storage point",
        )

        self.add_output(
            f"{resource_name}_missed_load",
            copy_shape=f"{resource_name}_in",
            units=self.config.resource_rate_units,
            desc=f"{resource_name} missed load timeseries",
        )

    def compute(self, inputs, outputs):
        """
        Compute the state of charge (SOC) and output flow based on demand and storage constraints.

        """
        resource_name = self.config.resource_name
        max_capacity = self.config.max_capacity
        max_charge_percent = self.config.max_charge_percent
        min_charge_percent = self.config.min_charge_percent
        init_charge_percent = self.config.init_charge_percent
        max_charge_rate = self.config.max_charge_rate
        max_discharge_rate = self.config.max_discharge_rate
        charge_efficiency = self.config.charge_efficiency
        discharge_efficiency = self.config.discharge_efficiency

        # Initialize time-step state of charge prior to loop so the loop starts with
        # the previous time step's value
        soc = deepcopy(init_charge_percent)

        demand_profile = inputs[f"{resource_name}_demand_profile"]

        # initialize outputs
        soc_array = outputs[f"{resource_name}_soc"]
        curtailment_array = outputs[f"{resource_name}_curtailed"]
        output_array = outputs[f"{resource_name}_out"]
        missed_load_array = outputs[f"{resource_name}_missed_load"]

        # Loop through each time step
        for t, demand_t in enumerate(demand_profile):
            # Get the input flow at the current time step
            input_flow = inputs[f"{resource_name}_in"][t]

            # Calculate the available charge/discharge capacity
            available_charge = (max_charge_percent - soc) * max_capacity
            available_discharge = (soc - min_charge_percent) * max_capacity

            # Initialize persistent variables for curtailment and missed load
            excess_input = 0.0
            charge = 0.0

            # Determine the output flow based on demand_t and SOC
            if demand_t > input_flow:
                # Discharge storage to meet demand.
                # `discharge_needed` is as seen by the storage
                discharge_needed = (demand_t - input_flow) / discharge_efficiency
                # `discharge` is as seen by the storage, but `max_discharge_rate` is as observed
                # outside the storage
                discharge = min(
                    discharge_needed, available_discharge, max_discharge_rate / discharge_efficiency
                )
                soc -= discharge / max_capacity  # soc is a ratio with value between 0 and 1
                # output is as observed outside the storage, so we need to adjust `discharge` by
                # applying `discharge_efficiency`.
                output_array[t] = input_flow + discharge * discharge_efficiency
            else:
                # Charge storage with excess input
                # `excess_input` is as seen outside the storage
                excess_input = input_flow - demand_t
                # `charge` is as seen by the storage, but the things being compared should all be as
                # seen outside the storage so we need to adjust `available_charge` outside the
                # storage view and the final result back into the storage view.
                charge = (
                    min(excess_input, available_charge / charge_efficiency, max_charge_rate)
                    * charge_efficiency
                )
                soc += charge / max_capacity  # soc is a ratio with value between 0 and 1
                output_array[t] = demand_t

            # Ensure SOC stays within bounds
            soc = max(min_charge_percent, min(max_charge_percent, soc))

            # Record the SOC for the current time step
            soc_array[t] = deepcopy(soc)

            # Record the curtailment at the current time step. Adjust `charge` from storage view to
            # outside view for curtailment
            curtailment_array[t] = max(0, float(excess_input - charge / charge_efficiency))

            # Record the missed load at the current time step
            missed_load_array[t] = max(0, (demand_t - output_array[t]))

        outputs[f"{resource_name}_out"] = output_array

        # Return the SOC
        outputs[f"{resource_name}_soc"] = soc_array

        # Return the curtailment
        outputs[f"{resource_name}_curtailed"] = curtailment_array

        # Return the missed load
        outputs[f"{resource_name}_missed_load"] = missed_load_array


@define
class PyomoOpenLoopControllerConfig(BaseConfig):
    """
    Configuration class for the DemandOpenLoopController.

    This class defines the parameters required to configure the `DemandOpenLoopController`.

    Attributes:
        resource_name (str): Name of the resource being controlled (e.g., "hydrogen").
        resource_units (str): Units of the resource (e.g., "kg/h").
        time_steps (int): Number of time steps in the simulation.
        max_capacity (float): Maximum storage capacity of the resource (in non-rate units,
            e.g., "kg" if `resource_units` is "kg/h").
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
        demand_profile (scalar or list): The demand values for each time step (in the same units
            as `resource_units`) or a scalar for a constant demand.
    """

    resource_name: str = field()
    resource_units: str = field()
    time_steps: int = field()
    max_capacity: float = field()
    max_charge_percent: float = field()
    min_charge_percent: float = field()
    init_charge_percent: float = field()
    max_charge_rate: float = field()
    max_discharge_rate: float = field()
    charge_efficiency: float = field()
    discharge_efficiency: float = field()
    demand_profile: int | float | list = field()


class PyomoOpenLoopController(ControllerBaseClass):
    def setup(self):
        self.config = PyomoOpenLoopControllerConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        self.add_input(
            f"{self.config.resource_name}_in",
            shape_by_conn=True,
            units=self.config.resource_units,
            desc=f"{self.config.resource_name} input timeseries from production to storage",
        )

        self.add_output(
            f"{self.config.resource_name}_out",
            copy_shape=f"{self.config.resource_name}_in",
            units=self.config.resource_units,
            desc=f"{self.config.resource_name} output timeseries from plant after storage",
        )

        self.add_output(  # using non-discrete outputs so shape and units can be specified
            f"{self.config.resource_name}_soc",
            copy_shape=f"{self.config.resource_name}_in",
            units="unitless",
            desc=f"{self.config.resource_name} state of charge timeseries for storage",
        )

        self.add_output(  # using non-discrete outputs so shape and units can be specified
            f"{self.config.resource_name}_curtailed",
            copy_shape=f"{self.config.resource_name}_in",
            units=self.config.resource_units,
            desc=f"{self.config.resource_name} curtailment timeseries for inflow resource at \
                storage point",
        )

        self.add_output(  # using non-discrete outputs so shape and units can be specified
            f"{self.config.resource_name}_missed_load",
            copy_shape=f"{self.config.resource_name}_in",
            units=self.config.resource_units,
            desc=f"{self.config.resource_name} missed load timeseries",
        )

        # get technology group name
        tech_group_name = self.pathname.split(".")[-2]
        dispatch_connections = self.options["plant_config"]["tech_to_dispatch_connections"]
        for connection in dispatch_connections:
            source_tech, intended_dispatch_tech, object_name = connection
            if intended_dispatch_tech == tech_group_name:
                self.add_discrete_input(f"{object_name}_{source_tech}", val=None)
            else:
                continue

    def compute(
        self, inputs, outputs, discrete_inputs, discrete_outputs
    ):  # , discrete_inputs, discrete_outputs):
        """
        Compute the state of charge (SOC) and output flow based on demand and storage constraints.

        """
        demand_profile = self.config.demand_profile

        # if demand_profile is a scalar, then use it to create a constant timeseries
        if isinstance(demand_profile, (int, float)):
            demand_profile = [demand_profile] * self.config.time_steps

        import pdb

        pdb.set_trace()
        # outputs[f"{resource_name}_out"] = output_array
        # # Return the SOC
        # outputs[f"{resource_name}_soc"] = soc_array
        # # Return the curtailment
        # outputs[f"{resource_name}_curtailed"] = curtailment_array
        # # Return the missed load
        # outputs[f"{resource_name}_missed_load"] = missed_load_array
