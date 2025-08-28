from attrs import field, define
from dataclasses import dataclass, asdict
from typing import Optional, Sequence, List

import PySAM.BatteryStateful as BatteryStateful

from h2integrate.core.model_baseclasses import CostModelBaseClass
from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.storage.battery.battery_baseclass import BatteryPerformanceBaseClass

from hopp.utilities.validators import contains, gt_zero, range_val


@dataclass
class BatteryOutputs:
    I: Sequence
    P: Sequence
    Q: Sequence
    SOC: Sequence
    T_batt: Sequence
    gen: Sequence
    n_cycles: Sequence
    P_chargeable: Sequence
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
        n_cycles: number of rainflow cycles elapsed since start of simulation [1]
        P_chargeable: estimated max chargeable power [kW]

    The next outputs, an entry per timestep, are from the HOPP dispatch model, which are then
        passed to the simulation:
        dispatch_I: current [A], only applicable to battery dispatch models with current modeled
        dispatch_P: power [mW]
        dispatch_SOC: state-of-charge [%]
    
    This output has a different length, one entry per control window:
        dispatch_lifecycles_per_control_window: number of cycles per control window
    """

    def __init__(self, n_timesteps, n_control_window):
        """Class for storing stateful battery and dispatch outputs."""
        self.stateful_attributes = ['I', 'P', 'Q', 'SOC', 'T_batt', 'n_cycles', "P_chargeable"]
        for attr in self.stateful_attributes:
            setattr(self, attr, [0.0] * n_timesteps)

        dispatch_attributes = ['I', 'P', 'SOC']
        for attr in dispatch_attributes:
            setattr(self, 'dispatch_'+attr, [0.0] * n_timesteps)

        self.dispatch_lifecycles_per_control_window = [None] * int(n_timesteps / n_control_window)

    def export(self):
        return asdict(self)


@define
class PySAMBatteryPerformanceModelConfig(BaseConfig):
    """
    Configuration class for `Battery`.

    Args:
        tracking: default True -> `Battery`
        max_capacity: Battery energy capacity [kWh]
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
    max_capacity: float = field(validator=gt_zero)
    system_capacity_kw: float = field(validator=gt_zero)
    cost_year: int = field()
    system_model_source: str = field(default="pysam", validator=contains(["pysam", "hopp"]))
    chemistry: str = field(
        default="LFPGraphite",
        validator=contains(["LFPGraphite", "LMOLTO", "LeadAcid", "NMCGraphite", "LDES"])
    )
    tracking: bool = field(default=True)
    min_charge_percent: float = field(default=0.1, validator=range_val(0, 1))
    max_charge_percent: float = field(default=0.9, validator=range_val(0, 1))
    init_charge_percent: float = field(default=0.5, validator=range_val(0, 1))
    n_timesteps: int = field(default=8760)
    dt: float = field(default=1.0)
    n_control_window: int = field(default=24)
    n_horizon_window: int = field(default=48)
    name: str = field(default="Battery")


class PySAMBatteryPerformanceModel(BatteryPerformanceBaseClass, CostModelBaseClass):
    """
    An OpenMDAO component that wraps a WindPlant model.
    It takes wind parameters as input and outputs power generation data.
    """

    def setup(self):
        self.config = PySAMBatteryPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        BatteryPerformanceBaseClass.setup(self)
        CostModelBaseClass.setup(self)

        self.add_discrete_input(
            "control_variable",
            val="input_power",
            desc="Configure the control mode for the PySAM battery",
        )

        self.add_output(
            "P_chargeable",
            val=0.0,
            copy_shape="electricity_in",
            units="kW",
            desc="Estimated max chargeable power",
        )

        # Initialize the PySAM BatteryStateful model with defaults
        self.system_model = BatteryStateful.default(self.config.chemistry)

        n_timesteps = self.config.n_timesteps
        n_control_window = self.config.n_control_window

        # Setup outputs for the battery model to be stored during the compute method
        self.outputs = BatteryOutputs(n_timesteps=n_timesteps, n_control_window=n_control_window)

        # TODO: should this be made configurable by users?
        module_specs = {'capacity': 400, 'surface_area': 30} # 400 [kWh] -> 30 [m^2]

        # Size the battery based on inputs -> method brought from HOPP
        self.size_batterystateful(
            self.config.max_capacity,
            self.system_model.ParamsPack.nominal_voltage,
            module_specs=module_specs,
        )
        self.system_model.ParamsPack.h = 20
        self.system_model.ParamsPack.Cp = 900
        self.system_model.ParamsCell.resistance = 0.001
        self.system_model.ParamsCell.C_rate = (
            self.config.system_capacity_kw / self.config.max_capacity
        )

        # Minimum set of parameters to set to get statefulBattery to work
        self._set_control_mode()

        self.system_model.value("dt_hr", self.config.dt)
        # TODO: Make sure this should be multiplied by 100
        self.system_model.value("minimum_SOC", self.config.min_charge_percent * 100)
        self.system_model.value("maximum_SOC", self.config.max_charge_percent * 100)
        self.system_model.value("initial_SOC", self.config.init_charge_percent * 100)

        # Setup PySAM battery model using PySAM method
        self.system_model.setup()

        # create inputs for pyomo control model
        if "tech_to_dispatch_connections" in self.options["plant_config"]:
            # get technology group name
            self.tech_group_name = self.pathname.split(".")[-2]
            for _source_tech, intended_dispatch_tech in self.options["plant_config"][
                "tech_to_dispatch_connections"
            ]:
                if intended_dispatch_tech == self.tech_group_name:
                    self.add_discrete_input("pyomo_dispatch_solver", val=dummy_function)
                    break

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        if "pyomo_dispatch_solver" in discrete_inputs:
            # Simulate the battery with provided dispatch inputs
            dispatch = discrete_inputs["pyomo_dispatch_solver"]
            kwargs = {
                "time_step_duration": self.config.dt,
                "control_variable": discrete_inputs["control_variable"],
            }
            dispatch(self.simulate, kwargs, inputs)
        else:
            # Simulate the battery with provided inputs
            self.simulate(
                electricity_in=inputs["electricity_in"],
                time_step_duration=self.config.dt,
                control_variable=discrete_inputs["control_variable"],
            )

        # Store outputs from the battery model
        outputs["electricity_out"] = self.outputs.P
        outputs["SOC"] = self.outputs.SOC
        outputs["P_chargeable"] = self.outputs.P_chargeable

    def simulate(
            self,
            electricity_in: list,
            time_step_duration: list,
            control_variable: str,
            sim_start_index: int = 0,
        ):
        """Simulates the battery with the provided dispatch inputs.

        Args:
            electricity_in (list): Commanded power values from the dispatch algorithm.
            time_step_duration (list): The timestep for each dispatch value.
            control_variable (str): Determines the type of control for the battery, either
                "input_current" or "input_power". The `electricity_in` will need to match with
                either current values or power values.
        """
        # Loop through the provided input power/current (decided by control_variable)
        self.system_model.value('dt_hr', time_step_duration)
        for t in range(len(electricity_in)):
            self.system_model.value(control_variable, electricity_in[t])

            self.system_model.execute(0)

            # Store outputs based on the outputs defined in `BatteryOutputs` above. The values are
            # scraped from the PySAM model modules `StatePack` and `StateCell`.
            for attr in self.outputs.stateful_attributes:
                if (
                    hasattr(self.system_model.StatePack, attr)
                    or hasattr(self.system_model.StateCell, attr)
                ):
                    getattr(self.outputs, attr)[sim_start_index + t] = self.system_model.value(attr)


    def size_batterystateful(
            self,
            desired_capacity,
            desired_voltage,
            module_specs=None
        ):
        """Helper function for ``battery_model_sizing()``. Modifies BatteryStateful model with new
        sizing. For Battery model, use ``size_battery()`` instead. Only battery side DC sizing.

        :param float desired_capacity: kWhAC if AC-connected, kWhDC otherwise.
        :param float desired_voltage: Volts.
        :param dict module_specs: {capacity (float), surface_area (float)} Optional, module specs
            for scaling surface area.
        
            capacity: float
                Capacity of a single battery module in kWhAC if AC-connected, kWhDC otherwise.
            surface_area: float
                Surface area is of single battery module in m^2.

        :returns: Dictionary of sizing parameters.
        :rtype: dict
        """
        # calculate size
        if type(self.system_model) != BatteryStateful.BatteryStateful:
            raise TypeError

        original_capacity = self.system_model.ParamsPack.nominal_energy

        self.system_model.ParamsPack.nominal_voltage = desired_voltage
        self.system_model.ParamsPack.nominal_energy = desired_capacity

        # calculate thermal
        thermal_inputs = {
            'mass': self.system_model.ParamsPack.mass,
            'surface_area': self.system_model.ParamsPack.surface_area,
            'original_capacity': original_capacity,
            'desired_capacity': desired_capacity
        }
        if module_specs is not None:
            module_specs = {'module_'+k: v for k, v in module_specs.items()}
            thermal_inputs.update(module_specs)

        thermal_outputs = self.calculate_thermal_params(thermal_inputs)

        self.system_model.ParamsPack.mass = thermal_outputs['mass']
        self.system_model.ParamsPack.surface_area = thermal_outputs['surface_area']


    def calculate_thermal_params(self, input_dict):
        """Calculates the mass and surface area of a battery by calculating from its current
        parameters the mass / specific energy and volume / specific energy ratios. If
        module_capacity and module_surface_area are provided, battery surface area is calculated by
        scaling module_surface_area by the number of modules required to fulfill desired capacity.
    
        :param dict input_dict: A dictionary of battery thermal parameters at original size.
            {mass (float), surface_area (float), original_capacity (float), desired_capacity
            (float), module_capacity (float, optional), surface_area (float, optional)}.

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


    def _set_control_mode(
            self,
            control_mode: float=1.0,
            input_power: float=0.0,
            input_current: float=0.0,
            control_variable: str="input_power"
        ):
        """Sets control mode."""
        if isinstance(self.system_model, BatteryStateful.BatteryStateful):
            # Power control = 1.0, current control = 0.0
            self.system_model.value("control_mode", control_mode)
            # Need initial values
            self.system_model.value("input_power", input_power)
            self.system_model.value("input_current", input_current)
            # Either `input_power` or `input_current`; need to adjust `control_mode` above
            self.control_variable = control_variable


def dummy_function():
    # this function is required for initialzing the pyomo control input and nothing else
    pass