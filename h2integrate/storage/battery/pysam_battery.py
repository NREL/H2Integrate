from attrs import field, define
from dataclasses import dataclass, asdict
from typing import Optional, Sequence, List, Union

import numpy as np

import PySAM.BatteryStateful as BatteryStateful

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.storage.battery.battery_baseclass import BatteryPerformanceBaseClass

# from hopp.simulation.technologies.financial import FinancialModelType
# from hopp.simulation.technologies.battery import Battery
from hopp.utilities.validators import contains, gt_zero, range_val


n_timesteps = 8760
n_periods_per_day = n_timesteps // 365
n_roll_periods = 24


@dataclass
class BatteryOutputs:
    I: Sequence
    P: Sequence
    Q: Sequence
    SOC: Sequence
    T_batt: Sequence
    gen: Sequence
    n_cycles: Sequence
    dispatch_I: List[float]
    dispatch_P: List[float]
    dispatch_SOC: List[float]
    dispatch_lifecycles_per_day: List[Optional[int]]
    """
    The following outputs are simulated from the BatteryStateful model, an entry per timestep:
        I: current [A]
        P: power [kW]
        Q: capacity [Ah]
        SOC: state-of-charge [%]
        T_batt: temperature [C]
        gen: same as P
        n_cycles: number of rainflow cycles elapsed since start of simulation [1]

    The next outputs, an entry per timestep, are from the HOPP dispatch model, which are then passed to the simulation:
        dispatch_I: current [A], only applicable to battery dispatch models with current modeled
        dispatch_P: power [mW]
        dispatch_SOC: state-of-charge [%]
    
    This output has a different length, one entry per day:
        dispatch_lifecycles_per_day: number of cycles per day
    """

    def __init__(self, n_timesteps, n_periods_per_day):
        """Class for storing stateful battery and dispatch outputs."""
        self.stateful_attributes = ['I', 'P', 'Q', 'SOC', 'T_batt', 'gen', 'n_cycles']
        for attr in self.stateful_attributes:
            setattr(self, attr, [0.0] * n_timesteps)

        dispatch_attributes = ['I', 'P', 'SOC']
        for attr in dispatch_attributes:
            setattr(self, 'dispatch_'+attr, [0.0] * n_timesteps)

        self.dispatch_lifecycles_per_day = [None] * int(n_timesteps / n_periods_per_day)

    def export(self):
        return asdict(self)


@define
class PySAMBatteryPerformanceModelConfig(BaseConfig):
    """
    Configuration class for `Battery`.

    Args:
        tracking: default True -> `Battery`
        system_capacity_kwh: Battery energy capacity [kWh]
        system_capacity_kw: Battery rated power capacity [kW]
        system_model_source: software source for the system model, can by 'pysam' or 'hopp'
        chemistry: Battery chemistry option

            PySAM options:
                - "LFPGraphite" (default)
                - "LMOLTO"
                - "LeadAcid" 
                - "NMCGraphite"
            HOPP options:
                - "LDES" generic long-duration energy storage
        minimum_SOC: Minimum state of charge [%]
        maximum_SOC: Maximum state of charge [%]
        initial_SOC: Initial state of charge [%]
    """
    system_capacity_kwh: float = field(validator=gt_zero)
    system_capacity_kw: float = field(validator=gt_zero)
    system_model_source: str = field(default="pysam", validator=contains(["pysam", "hopp"]))
    chemistry: str = field(
        default="LFPGraphite",
        validator=contains(["LFPGraphite", "LMOLTO", "LeadAcid", "NMCGraphite", "LDES"])
    )
    tracking: bool = field(default=True)
    minimum_SOC: float = field(default=10, validator=range_val(0, 100))
    maximum_SOC: float = field(default=90, validator=range_val(0, 100))
    initial_SOC: float = field(default=10, validator=range_val(0, 100))
    name: str = field(default="Battery")


# @define
# class PySAMBatteryPerformanceModelSiteConfig(BaseConfig):
#     """Configuration class for the location of the battery
#         PySAMBatteryPerformanceComponentSite.

#     Args:
#         latitude (float): Latitude of wind plant location.
#         longitude (float): Longitude of wind plant location.
#         year (float): Year for resource.
#     """

#     latitude: float = field()
#     longitude: float = field()
#     year: float = field()


class PySAMBatteryPerformanceModel(BatteryPerformanceBaseClass):
    """
    An OpenMDAO component that wraps a WindPlant model.
    It takes wind parameters as input and outputs power generation data.
    """

    def setup(self):
        super().setup()
        print(self.options["tech_config"])
        self.config = PySAMBatteryPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        self.system_model = BatteryStateful.default(self.config.chemistry)

        self.outputs = BatteryOutputs(n_timesteps=n_timesteps, n_periods_per_day=n_periods_per_day)

        # TODO: should this be made configurable by users?
        module_specs = {'capacity': 400, 'surface_area': 30} # 400 [kWh] -> 30 [m^2]

        size_batterystateful(
            self.system_model,
            self.config.system_capacity_kw,
            self.config.system_capacity_kwh,
            self.system_model.ParamsPack.nominal_voltage,
            module_specs=module_specs,
        )
        self.system_model.ParamsPack.h = 20
        self.system_model.ParamsPack.Cp = 900
        self.system_model.ParamsCell.resistance = 0.001
        self.system_model.ParamsCell.C_rate = (
            self.config.system_capacity_kw / self.config.system_capacity_kwh
        )

        # Minimum set of parameters to set to get statefulBattery to work
        self.system_model.value("control_mode", 1.0)
        self.system_model.value("input_power", 0.0)
        self.system_model.value("input_current", 0.0)

        self.system_model.value("dt_hr", 1.0)
        self.system_model.value("minimum_SOC", self.config.minimum_SOC)
        self.system_model.value("maximum_SOC", self.config.maximum_SOC)
        self.system_model.value("initial_SOC", self.config.initial_SOC)

        # Setup PySAM battery model using PySAM method
        self.system_model.setup()

    def compute(self, inputs, outputs):
        # hybrid_dispatch_builder_solver.py -----------------------------------#
        ti = list(range(0, n_timesteps, n_roll_periods))

        # for i, t in enumerate(ti):
            # if self.options.is_test_start_year or self.options.is_test_end_year:
            #     if (self.options.is_test_start_year and i < 5) or (
            #         self.options.is_test_end_year and i > 359
            #     ):
                    # start_time = time.time()
                    # self.simulate_with_dispatch(t)
                    # sim_w_dispath_time = time.time()
                    # logger.info("Day {} dispatch optimized.".format(i))
                    # logger.info(
                    #     "      %6.2f seconds required to simulate with dispatch"
                    #     % (sim_w_dispath_time - start_time)
                    # )
                # else:
                #     continue
                    # TODO: can we make the csp and battery model run with heuristic dispatch here?
                    #  Maybe calling a simulate_with_heuristic() method
            # else:
                # if (i % 73) == 0:
                #     logger.info("\t {:.0f} % complete".format(i * 20 / 73))
                # self.simulate_with_dispatch(t)
        for t in ti:
            self.hdbs_simulate_with_dispatch(t)

    # battery.py --------------------------------------------------------------#
    def battery_simulate_with_dispatch(self, n_periods: int, sim_start_time: Optional[int] = None):
        control = [pow_MW*1e3 for pow_MW in self.dispatch.power] # MW -> kW

        time_step_duration = self.dispatch.time_duration
        for t in range(n_periods):
            self.system_model.value('dt_hr', time_step_duration[t])
            self.system_model.value(self.dispatch.control_variable, control[t])

            # Only store information if passed the previous day simulations (used in clustering)
            if sim_start_time is not None:
                index_time_step = sim_start_time + t  # Store information
            else:
                index_time_step = None

            self.system_model.execute(0)

            if index_time_step is not None:
                for attr in self.outputs.stateful_attributes:
                    if hasattr(self.system_model.StatePack, attr) or hasattr(self.system_model.StateCell, attr):
                        getattr(self.outputs, attr)[index_time_step] = self.system_model.value(attr)
                    elif attr == 'gen':
                        getattr(self.outputs, attr)[index_time_step] = self.system_model.value('P')

    # hybrid_dispatch_builder_solver.py ---------------------------------------#
    def hdbs_simulate_with_dispatch(
        self,
        start_time: int,
        n_days: int = 1,
        initial_soc: float = None,
        n_initial_sims: int = 0,
    ):
        # this is needed for clustering effort
        update_dispatch_times = list(
            range(
                start_time,
                start_time + n_days * n_periods_per_day,
                n_roll_periods,
            )
        )

        for i, sim_start_time in enumerate(update_dispatch_times):
            self.update_dispatch_initial_soc(initial_soc=initial_soc)
            initial_soc = None

            self.update_time_series_parameters(sim_start_time)

            if self.site.follow_desired_schedule:
                n_horizon = len(self.power_sources["grid"].dispatch.blocks.index_set())
                if start_time + n_horizon > len(self.site.desired_schedule):
                    system_limit = list(self.site.desired_schedule[start_time:])
                    system_limit.extend(
                        list(
                            self.site.desired_schedule[
                                0 : n_horizon - len(system_limit)
                            ]
                        )
                    )
                else:
                    system_limit = self.site.desired_schedule[
                        start_time : start_time + n_horizon
                    ]

                transmission_limit = (
                    self.power_sources["grid"].value("grid_interconnection_limit_kwac")
                    / 1e3
                )
                for count, value in enumerate(system_limit):
                    if value > transmission_limit:
                        logger.warning(
                            "Warning: Desired schedule is greater than transmission limit. "
                            "Overwriting schedule to transmission limit"
                        )
                        system_limit[count] = transmission_limit

                self.power_sources["grid"].dispatch.generation_transmission_limit = (
                    system_limit
                )

            self.battery_heuristic()

            battery_sim_start_time = sim_start_time
            if i < n_initial_sims:
                battery_sim_start_time = None

            # simulate using dispatch solution
            self.battery_simulate_with_dispatch(
                n_roll_periods, sim_start_time=battery_sim_start_time
            )

            # Store Dispatch model values
            if sim_start_time is not None:
                time_slice = slice(sim_start_time, sim_start_time + self.options.n_roll_periods)
                self.outputs.dispatch_SOC[time_slice] = self.dispatch.soc[0:n_roll_periods]
                self.outputs.dispatch_P[time_slice] = self.dispatch.power[0:n_roll_periods]
                self.outputs.dispatch_I[time_slice] = self.dispatch.current[0:n_roll_periods]

    # hybrid_dispatch_builder_solver.py ---------------------------------------#
    def battery_heuristic(self):
        tot_gen = np.zeros(self.options.n_look_ahead_periods)

        for power_source in self.power_sources.keys():
            if "battery" in power_source or "grid" in power_source:
                continue
            
            tot_gen += self.power_sources[power_source].dispatch.available_generation

        tot_gen = tot_gen.tolist()
        
        grid_limit = self.power_sources["grid"].dispatch.generation_transmission_limit

        if "one_cycle" in self.options.battery_dispatch:
            # Get prices for one cycle heuristic
            prices = self.power_sources["grid"].dispatch.electricity_sell_price
            self.power_sources["battery"].dispatch.prices = prices

        if "load_following" in self.options.battery_dispatch:
            # TODO: Look into how to define a system as load following or not in the config file
            required_keys = ["desired_load"]
            if self.site.follow_desired_schedule:
                # Get difference between baseload demand and power generation and control scenario variables
                load_value = grid_limit
                load_difference = [
                    (load_value[x] - tot_gen[x]) for x in range(len(tot_gen))
                ]
                self.power_sources["battery"].dispatch.load_difference = load_difference
            else:
                raise ValueError(
                    type(self).__name__ + " requires the following : desired_schedule"
                )
            # Adding goal_power for the simple battery heuristic method for power setpoint tracking
            goal_power = [load_value] * self.options.n_look_ahead_periods
            ### Note: the inputs grid_limit and goal_power are in MW ###
            self.power_sources["battery"].dispatch.set_fixed_dispatch(
                tot_gen, grid_limit, load_value
            )
        else:
            self.power_sources["battery"].dispatch.set_fixed_dispatch(
                tot_gen, grid_limit
            )

    # simple_battery_dispatch.py ------------------------------------------------#
    def update_dispatch_initial_soc(self, initial_soc: float = None):
            """Updates dispatch initial state of charge (SOC).

            Args:
                initial_soc (float, optional): Initial state of charge. Defaults to None.

            """
            if initial_soc is not None:
                self.system_model.value("initial_SOC", initial_soc)
                self.system_model.setup()  # TODO: Do I need to re-setup stateful battery?
            self.initial_soc = self.system_model.value("SOC")

    def update_time_series_parameters(self, start_time: int):
        """Updates time series parameters.

        Args:
            start_time (int): The start time.

        """
        # TODO: provide more control
        self.time_duration = [1.0] * len(self.dispatch.blocks.index_set())

# battery_tools.py --------------------------------------------#
def size_batterystateful(
        model: BatteryStateful,
        _,
        desired_capacity,
        desired_voltage,
        module_specs=None
    ):
    """Helper function for ``battery_model_sizing()``. Modifies BatteryStateful model with new
    sizing. For Battery model, use ``size_battery()`` instead. Only battery side DC sizing.
    
    :param model: PySAM.Battery model
    :param _: Not used.
    :param float desired_capacity: kWhAC if AC-connected, kWhDC otherwise.
    :param float desired_voltage: Volts.
    :param dict module_specs: {capacity (float), surface_area (float)} Optional, module specs for
        scaling surface area.
    
        capacity: float
            Capacity of a single battery module in kWhAC if AC-connected, kWhDC otherwise.
        surface_area: float
            Surface area is of single battery module in m^2.

    :returns: Dictionary of sizing parameters.
    :rtype: dict
    """

    #
    # calculate size
    #
    if type(model) != BatteryStateful.BatteryStateful:
        raise TypeError

    original_capacity = model.ParamsPack.nominal_energy

    model.ParamsPack.nominal_voltage = desired_voltage
    model.ParamsPack.nominal_energy = desired_capacity

    #
    # calculate thermal
    #
    thermal_inputs = {
        'mass': model.ParamsPack.mass,
        'surface_area': model.ParamsPack.surface_area,
        'original_capacity': original_capacity,
        'desired_capacity': desired_capacity
    }
    if module_specs is not None:
        module_specs = {'module_'+k: v for k, v in module_specs.items()}
        thermal_inputs.update(module_specs)

    thermal_outputs = calculate_thermal_params(thermal_inputs)

    model.ParamsPack.mass = thermal_outputs['mass']
    model.ParamsPack.surface_area = thermal_outputs['surface_area']


def calculate_thermal_params(input_dict):
    """Calculates the mass and surface area of a battery by calculating from its current parameters
    the mass / specific energy and volume / specific energy ratios. If module_capacity and
    module_surface_area are provided, battery surface area is calculated by scaling
    module_surface_area by the number of modules required to fulfill desired capacity.
   
    :param dict input_dict: A dictionary of battery thermal parameters at original size.
        {mass (float), surface_area (float), original_capacity (float), desired_capacity (float),
        module_capacity (float, optional), surface_area (float, optional)}

        mass: float
            kg of battery at original size
        surface_area: float
            m^2 of battery at original size
        original_capacity: float
            Wh of battery
        desired_capacity: float
            Wh of new battery size
        module_capacity: float, optional
            Wh of module battery size
        module_surface_area: float, optional
            m^2 of module battery

    :returns: Dictionary of battery mass and surface area at desired size.
    :rtype: dict {mass (float), surface_area (float)} 

        mass: float
            kg of battery at desired size
        surface_area: float
            m^2 of battery at desired size
    """

    mass = input_dict['mass']
    surface_area = input_dict['surface_area']
    original_capacity = input_dict['original_capacity']
    desired_capacity = input_dict['desired_capacity']

    mass_per_specific_energy = mass / original_capacity

    volume = (surface_area / 6) ** (3/2)

    volume_per_specific_energy = volume / original_capacity

    output_dict = {
        'mass': mass_per_specific_energy * desired_capacity,
        'surface_area': (volume_per_specific_energy * desired_capacity) ** (2/3) * 6,
    }

    if input_dict.keys() >= {'module_capacity', 'module_surface_area'}:
        module_capacity = input_dict['module_capacity']
        module_surface_area = input_dict['module_surface_area']
        output_dict['surface_area'] = module_surface_area*desired_capacity/module_capacity

    return output_dict


