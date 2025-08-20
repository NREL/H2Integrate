from typing import TYPE_CHECKING, Union

import pyomo.environ as pyomo
import PySAM.BatteryStateful as BatteryStateful
from attrs import field, define
from pyomo.environ import units as u

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.control.control_strategies.controller_baseclass import ControllerBaseClass


if TYPE_CHECKING:  # to avoid circular imports
    from h2integrate.control.control_rules.pyomo_control_options import PyomoControlOptions


@define
class PyomoControllerBaseConfig(BaseConfig):
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
    resource_rate_units: str = field()
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
    # added by cbay, moved here by jthomas
    include_lifecycle_count: bool = field(default=False)


# class PyomoControllerBaseClass1(ControllerBaseClass):
#     def setup(self):
#         self.config = PyomoControllerBaseConfig.from_dict(
#             merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
#         )

#         self.add_input(
#             f"{self.config.resource_name}_in",
#             shape_by_conn=True,
#             units=self.config.resource_units,
#             desc=f"{self.config.resource_name} input timeseries from production to storage",
#         )

#         self.add_output(
#             f"{self.config.resource_name}_out",
#             copy_shape=f"{self.config.resource_name}_in",
#             units=self.config.resource_units,
#             desc=f"{self.config.resource_name} output timeseries from plant after storage",
#         )

#         self.add_output(  # using non-discrete outputs so shape and units can be specified
#             f"{self.config.resource_name}_soc",
#             copy_shape=f"{self.config.resource_name}_in",
#             units="unitless",
#             desc=f"{self.config.resource_name} state of charge timeseries for storage",
#         )

#         self.add_output(  # using non-discrete outputs so shape and units can be specified
#             f"{self.config.resource_name}_curtailed",
#             copy_shape=f"{self.config.resource_name}_in",
#             units=self.config.resource_units,
#             desc=f"{self.config.resource_name} curtailment timeseries for inflow resource at \
#                 storage point",
#         )

#         self.add_output(  # using non-discrete outputs so shape and units can be specified
#             f"{self.config.resource_name}_missed_load",
#             copy_shape=f"{self.config.resource_name}_in",
#             units=self.config.resource_units,
#             desc=f"{self.config.resource_name} missed load timeseries",
#         )

#         # get technology group name
#         tech_group_name = self.pathname.split(".")[-2]
#         dispatch_connections = self.options["plant_config"]["tech_to_dispatch_connections"]
#         for connection in dispatch_connections:
#             source_tech, intended_dispatch_tech, object_name = connection
#             if intended_dispatch_tech == tech_group_name:
#                 self.add_discrete_input(f"{object_name}_{source_tech}", val=None)
#             else:
#                 continue

#     def compute(
#         self, inputs, outputs, discrete_inputs, discrete_outputs
#     ):  # , discrete_inputs, discrete_outputs):
#         """
#         Compute the state of charge (SOC) and output flow based on demand and storage constraints.

#         """
#         demand_profile = self.config.demand_profile

#         # if demand_profile is a scalar, then use it to create a constant timeseries
#         if isinstance(demand_profile, (int, float)):
#             demand_profile = [demand_profile] * self.config.time_steps

#         # outputs[f"{resource_name}_out"] = output_array
#         # # Return the SOC
#         # outputs[f"{resource_name}_soc"] = soc_array
#         # # Return the curtailment
#         # outputs[f"{resource_name}_curtailed"] = curtailment_array
#         # # Return the missed load
#         # outputs[f"{resource_name}_missed_load"] = missed_load_array


def dummy_function():
    return None


class PyomoControllerBaseClass(ControllerBaseClass):
    def dummy_method(self):
        return None

    def setup(self):
        self.config = PyomoControllerBaseConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        # if demand_profile is a scalar, then use it to create a constant timeseries
        self.demand_profile = self.config.demand_profile
        if isinstance(self.demand_profile, (int, float)):
            self.demand_profile = [self.demand_profile] * self.config.time_steps

        # get technology group name
        tech_group_name = self.pathname.split(".")[-2]

        # create inputs for all pyomo object creation functions from all connected technologies
        dispatch_connections = self.options["plant_config"]["tech_to_dispatch_connections"]
        for connection in dispatch_connections:
            source_tech, intended_dispatch_tech, object_name = connection
            if intended_dispatch_tech == tech_group_name:
                self.add_discrete_input(f"{object_name}_{source_tech}", val=self.dummy_method)
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
        pyomo_model = pyomo.ConcreteModel()

        # run each pyomo rule set up function for each technology
        for key in discrete_inputs:
            discrete_inputs[key](pyomo_model)

        # define dispatch solver
        def pyomo_dispatch_solver(performance_model: callable, kwargs, pyomo_model=pyomo_model):
            return performance_model(kwargs)

        return pyomo_dispatch_solver

    # def pyomo_setup(self,
    #         pyomo_model: pyomo.ConcreteModel,
    #         index_set: pyomo.Set,
    #         system_model,
    #         block_set_name: str = "dispatch",):

    #     self.block_set_name = block_set_name
    #     self.round_digits = int(4)

    #     self._model = pyomo_model
    #     self._blocks = pyomo.Block(index_set, rule=self.dispatch_block_rule)
    #     setattr(self.model, self.block_set_name, self.blocks)

    #     self._system_model = system_model

    #     def dispatch_function(performance_model, kwargs, pyomo_model=pyomo_model):

    #         pass
    #         # for
    #         #     for
    #         #         pyomo
    #         #         performance

    #         # return output(s)_timeseries

    #     return dispatch_function

    @staticmethod
    def dispatch_block_rule(block, t):
        raise NotImplementedError("This function must be overridden for specific dispatch model")

    def initialize_parameters(self):
        raise NotImplementedError("This function must be overridden for specific dispatch model")

    def update_time_series_parameters(self, start_time: int):
        raise NotImplementedError("This function must be overridden for specific dispatch model")

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


class SimpleBatteryControllerHeuristic(PyomoControllerBaseClass):
    """Fixes battery dispatch operations based on user input.

    Currently, enforces available generation and grid limit assuming no battery charging from grid.

    """

    def pyomo_setup(
        self,
        pyomo_model: pyomo.ConcreteModel,
        index_set: pyomo.Set,
        system_model: BatteryStateful.BatteryStateful,
        fixed_dispatch: list | None = None,
        block_set_name: str = "heuristic_battery",
        control_options: dict | None = None,
    ):
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
        if control_options is None:
            control_options = {}

        super().pyomo_setup(
            pyomo_model,
            index_set,
            system_model,
            block_set_name=block_set_name,
        )

        self._create_soc_linking_constraint()

        # TODO: implement and test lifecycle counting
        # TODO: we could remove this option and just have lifecycle count default
        # self.control_options = control_options
        # if self.control_options.include_lifecycle_count:
        #     self._create_lifecycle_model()
        #     if self.control_options.max_lifecycle_per_day < np.inf:
        #         self._create_lifecycle_count_constraint()

        self.max_charge_fraction = list([0.0] * len(self.blocks.index_set()))
        self.max_discharge_fraction = list([0.0] * len(self.blocks.index_set()))
        self.user_fixed_dispatch = list([0.0] * len(self.blocks.index_set()))
        # TODO: should I enforce either a day schedule or a year schedule year and save it as
        # user input? Additionally, Should I drop it as input in the init function?
        if fixed_dispatch is not None:
            self.user_fixed_dispatch = fixed_dispatch

        self._fixed_dispatch = list([0.0] * len(self.blocks.index_set()))

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
        # NOTE: `_system_model` format copied from HOPP, largely influenced by PySAM
        self.minimum_soc = self._system_model.value("minimum_SOC")
        self.maximum_soc = self._system_model.value("maximum_SOC")
        self.initial_soc = self._system_model.value("initial_SOC")

        self._set_control_mode()
        self._set_model_specific_parameters()

    def dispatch_block_rule(self, storage: pyomo.ConcreteModel):
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

    def _set_control_mode(self):
        """Sets control mode."""
        # NOTE: storage specific code here
        if isinstance(self._system_model, BatteryStateful.BatteryStateful):
            self._system_model.value("control_mode", 1.0)  # Power control
            self._system_model.value("input_power", 0.0)
            self.control_variable = "input_power"

    def _set_model_specific_parameters(self, round_trip_efficiency=88.0):
        """Sets model-specific parameters.

        Args:
            round_trip_efficiency (float, optional): The round-trip efficiency including
                converter efficiency. Defaults to 88.0, which includes converter efficiency.

        """
        # NOTE: storage specific code here
        self.round_trip_efficiency = round_trip_efficiency  # Including converter efficiency
        self.capacity = self._system_model.value("nominal_energy")  # / 1e3  # [MWh]

    def _create_soc_linking_constraint(self):
        """Creates state-of-charge linking constraint."""
        ##################################
        # Parameters                     #
        ##################################
        self.model.initial_soc = pyomo.Param(
            doc=self.block_set_name + " initial state-of-charge at beginning of the horizon[-]",
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

    def set_fixed_dispatch(self, gen: list, grid_limit: list):
        """Sets charge and discharge amount of storage dispatch using fixed_dispatch attribute
            and enforces available generation and grid limits.

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
        """Set storage charge and discharge fraction limits based on
        available generation and grid capacity, respectively.

        Args:
            gen (list): Generation blocks.
            grid_limit (list): Grid capacity.

        NOTE: This method assumes that storage cannot be charged by the grid.

        """
        for t in self.blocks.index_set():
            self.max_charge_fraction[t] = self.enforce_power_fraction_simple_bounds(
                gen[t] / self.maximum_storage
            )
            self.max_discharge_fraction[t] = self.enforce_power_fraction_simple_bounds(
                (grid_limit[t] - gen[t]) / self.maximum_storage
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
                * (1 / (self.discharge_efficiency / 100.0) * discharge_resource)
                / self.capacity
            )
        elif storage_fraction < 0.0:
            charge_resource = -storage_fraction * self.maximum_storage
            soc = (
                soc0
                + self.time_duration[0]
                * (self.charge_efficiency / 100.0 * charge_resource)
                / self.capacity
            )
        else:
            soc = soc0

        min_soc = self._system_model.value("minimum_SOC") / 100
        max_soc = self._system_model.value("maximum_SOC") / 100

        soc = max(min_soc, min(max_soc, soc))

        return soc

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
        soc0 = self.model.initial_soc.value
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
        if initial_soc > 1:
            initial_soc /= 100.0
        initial_soc = round(initial_soc, self.round_digits)
        if initial_soc > self.maximum_soc / 100:
            print(
                "Warning: Storage dispatch was initialized with a state-of-charge greater than "
                "maximum value!"
            )
            print(f"Initial SOC = {initial_soc}")
            print("Initial SOC was set to maximum value.")
            initial_soc = self.maximum_soc / 100
        elif initial_soc < self.minimum_soc / 100:
            print(
                "Warning: Storage dispatch was initialized with a state-of-charge less than "
                "minimum value!"
            )
            print(f"Initial SOC = {initial_soc}")
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
            raise ValueError("fixed_dispatch must be the same length as dispatch index set.")
        elif max(fixed_dispatch) > 1.0 or min(fixed_dispatch) < -1.0:
            raise ValueError("fixed_dispatch must be normalized values between -1 and 1.")
        else:
            self._user_fixed_dispatch = fixed_dispatch

    @property
    def storage_amount(self) -> list:
        """Storage amount."""
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
    #     return self.storage_amount

    @property
    def soc(self) -> list:
        """State-of-charge."""
        return [self.blocks[t].soc.value * 100.0 for t in self.blocks.index_set()]

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

    @property
    def round_trip_efficiency(self) -> float:
        """Round trip efficiency."""
        return self.charge_efficiency * self.discharge_efficiency / 100.0

    @round_trip_efficiency.setter
    def round_trip_efficiency(self, round_trip_efficiency: float):
        round_trip_efficiency = self._check_efficiency_value(round_trip_efficiency)
        # Assumes equal charge and discharge efficiencies
        efficiency = round_trip_efficiency ** (1 / 2)
        self.charge_efficiency = efficiency
        self.discharge_efficiency = efficiency


# @define
# class HeuristicLoadFollowingControllerConfig(BaseConfig):
#     resource_name: str = field()
#     resource_units: str = field()
#     resource_rate_units: str = field()
#     system_capacity_kw: int = field()
#     include_lifecycle_count: bool = field(default=False)


class HeuristicLoadFollowingController(SimpleBatteryControllerHeuristic):
    """Operates the battery based on heuristic rules to meet the demand profile based power
        available from power generation profiles and power demand profile.

    Currently, enforces available generation and grid limit assuming no battery charging from grid.

    """

    def setup(
        self,
        pyomo_model: pyomo.ConcreteModel,
        index_set: pyomo.Set,
        system_model: BatteryStateful.BatteryStateful,
        fixed_dispatch: list | None = None,
        block_set_name: str = "heuristic_load_following_battery",
        control_options: Union[dict, "PyomoControlOptions"] | None = None,
    ):
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
        self.config = PyomoControllerBaseConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "control")
        )

        super().setup(
            pyomo_model,
            index_set,
            system_model,
            fixed_dispatch,
            block_set_name,
            control_options,
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

    def _heuristic_method(self, gen, goal_resource):
        """Enforces storage fraction limits and sets _fixed_dispatch attribute.
        Sets the _fixed_dispatch based on goal_resource and gen.

        Args:
            gen: Resource generation profile.
            goal_resource: Goal amount of resource.

        """
        for t in self.blocks.index_set():
            fd = (goal_resource[t] - gen[t]) / self.maximum_storage
            if fd > 0.0:  # Discharging
                if fd > self.max_discharge_fraction[t]:
                    fd = self.max_discharge_fraction[t]
            elif fd < 0.0:  # Charging
                if -fd > self.max_charge_fraction[t]:
                    fd = -self.max_charge_fraction[t]
            self._fixed_dispatch[t] = fd
