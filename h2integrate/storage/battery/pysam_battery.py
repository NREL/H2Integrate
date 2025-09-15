from dataclasses import asdict, dataclass
from collections.abc import Sequence

import numpy as np
import PySAM.BatteryStateful as BatteryStateful
from attrs import field, define
from hopp.utilities.validators import gt_zero, contains, range_val

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.model_baseclasses import CostModelBaseClass
from h2integrate.storage.battery.battery_baseclass import BatteryPerformanceBaseClass


@dataclass
class BatteryOutputs:
    I: Sequence  # noqa: E741
    P: Sequence
    Q: Sequence
    SOC: Sequence
    T_batt: Sequence
    gen: Sequence
    n_cycles: Sequence
    P_chargeable: Sequence
    P_dischargeable: Sequence
    dispatch_I: list[float]
    dispatch_P: list[float]
    dispatch_SOC: list[float]
    dispatch_lifecycles_per_day: list[int | None]
    unmet_demand: list[float]
    excess_resource: list[float]

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
        self.stateful_attributes = [
            "I",
            "P",
            "Q",
            "SOC",
            "T_batt",
            "n_cycles",
            "P_chargeable",
            "P_dischargeable",
        ]
        for attr in self.stateful_attributes:
            setattr(self, attr, [0.0] * n_timesteps)

        dispatch_attributes = ["I", "P", "SOC"]
        for attr in dispatch_attributes:
            setattr(self, "dispatch_" + attr, [0.0] * n_timesteps)

        self.dispatch_lifecycles_per_control_window = [None] * int(n_timesteps / n_control_window)

        self.component_attributes = ["unmet_demand", "excess_resource"]
        for attr in self.component_attributes:
            setattr(self, attr, [0.0] * n_timesteps)

    def export(self):
        return asdict(self)


@define
class PySAMBatteryPerformanceModelConfig(BaseConfig):
    """
    Configuration class for `Battery`.

    Args:
        tracking: default True -> `Battery`
        max_capacity: Battery energy capacity [kWh]
        rated_resource_capacity: Battery rated power capacity [kW]
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
        ref_module_capacity: reference module capacity in kWh
        ref_module_surface_area: reference module surface area in m^2
    """

    max_capacity: float = field(validator=gt_zero)
    rated_resource_capacity: float = field(validator=gt_zero)
    cost_year: int = field()
    system_model_source: str = field(default="pysam", validator=contains(["pysam", "hopp"]))
    chemistry: str = field(
        default="LFPGraphite",
        validator=contains(["LFPGraphite", "LMOLTO", "LeadAcid", "NMCGraphite", "LDES"]),
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
    ref_module_capacity: int | float = field(default=400)
    ref_module_surface_area: int | float = field(default=30)


class PySAMBatteryPerformanceModel(BatteryPerformanceBaseClass, CostModelBaseClass):
    """
    An OpenMDAO component that wraps a WindPlant model.
    It takes wind parameters as input and outputs power generation data.
    """

    def setup(self):
        self.config = PySAMBatteryPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        self.add_input(
            "charge_rate",
            val=self.config.rated_resource_capacity,
            units="kW/h",
            desc="Battery charge rate",
        )

        self.add_input(
            "storage_capacity",
            val=self.config.max_capacity,
            units="kW*h",
            desc="Battery storage capacity",
        )

        BatteryPerformanceBaseClass.setup(self)
        CostModelBaseClass.setup(self)

        self.add_discrete_input(
            "control_variable",
            val="input_power",
            desc="Configure the control mode for the PySAM battery",
        )

        self.add_input(
            "demand_in",
            val=0.0,
            copy_shape="electricity_in",
            units="kW",
            desc="Power demand",
        )

        self.add_output(
            "P_chargeable",
            val=0.0,
            copy_shape="electricity_in",
            units="kW",
            desc="Estimated max chargeable power",
        )

        self.add_output(
            "P_dischargeable",
            val=0.0,
            copy_shape="electricity_in",
            units="kW",
            desc="Estimated max dischargeable power",
        )

        self.add_output(
            "unmet_demand_out",
            val=0.0,
            copy_shape="electricity_in",
            units="kW/h",
            desc="Unmet power demand",
        )

        self.add_output(
            "excess_resource_out",
            val=0.0,
            copy_shape="electricity_in",
            units="kW/h",
            desc="Excess generated resource",
        )

        # Initialize the PySAM BatteryStateful model with defaults
        self.system_model = BatteryStateful.default(self.config.chemistry)

        n_timesteps = self.config.n_timesteps
        n_control_window = self.config.n_control_window

        # Setup outputs for the battery model to be stored during the compute method
        self.outputs = BatteryOutputs(n_timesteps=n_timesteps, n_control_window=n_control_window)

        # create inputs for pyomo control model
        if "tech_to_dispatch_connections" in self.options["plant_config"]:
            # get technology group name
            # TODO: The split below seems brittle
            self.tech_group_name = self.pathname.split(".")
            for _source_tech, intended_dispatch_tech in self.options["plant_config"][
                "tech_to_dispatch_connections"
            ]:
                if any(intended_dispatch_tech in name for name in self.tech_group_name):
                    self.add_discrete_input("pyomo_dispatch_solver", val=dummy_function)
                    break

        self.unmet_demand = 0.0
        self.excess_resource = 0.0

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # Size the battery based on inputs -> method brought from HOPP
        module_specs = {
            "capacity": self.config.ref_module_capacity,
            "surface_area": self.config.ref_module_surface_area,
        }

        self.size_batterystateful(
            inputs["storage_capacity"][0],
            self.system_model.ParamsPack.nominal_voltage,
            module_specs=module_specs,
        )
        self.system_model.ParamsPack.h = 20
        self.system_model.ParamsPack.Cp = 900
        self.system_model.ParamsCell.resistance = 0.001
        self.system_model.ParamsCell.C_rate = (
            inputs["charge_rate"][0] / inputs["storage_capacity"][0]
        )

        # Minimum set of parameters to set to get statefulBattery to work
        self._set_control_mode()

        self.system_model.value("dt_hr", self.config.dt)
        self.system_model.value("minimum_SOC", self.config.min_charge_percent * 100)
        self.system_model.value("maximum_SOC", self.config.max_charge_percent * 100)
        self.system_model.value("initial_SOC", self.config.init_charge_percent * 100)

        # Setup PySAM battery model using PySAM method
        self.system_model.setup()

        # Run PySAM battery model 1 timestep to initialize values
        self.system_model.value("dt_hr", 1.0)
        self.system_model.value("input_power", 0.0)
        self.system_model.execute(0)

        if "pyomo_dispatch_solver" in discrete_inputs:
            # Simulate the battery with provided dispatch inputs
            dispatch = discrete_inputs["pyomo_dispatch_solver"]
            kwargs = {
                "time_step_duration": self.config.dt,
                "control_variable": discrete_inputs["control_variable"],
            }
            power_out, unmet_demand, excess_resource, soc = dispatch(self.simulate, kwargs, inputs)
        else:
            # Simulate the battery with provided inputs
            self.simulate(
                storage_dispatch_commands=inputs["electricity_in"],
                time_step_duration=self.config.dt,
                control_variable=discrete_inputs["control_variable"],
            )
        # Store outputs from the battery model
        # TODO I'm not sure we should allow negative values here, but right now we do
        outputs["electricity_out"] = np.minimum(
            inputs["demand_in"],
            inputs["electricity_in"] + power_out,  # self.outputs.P
        )
        outputs["SOC"] = soc  # self.outputs.SOC
        outputs["P_chargeable"] = self.outputs.P_chargeable
        outputs["P_dischargeable"] = self.outputs.P_dischargeable
        outputs["unmet_demand_out"] = unmet_demand  # self.outputs.unmet_demand
        outputs["excess_resource_out"] = excess_resource  # self.outputs.excess_resource
        outputs["battery_electricity_out"] = power_out  # self.outputs.P

    def simulate(
        self,
        storage_dispatch_commands: list,
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
        self.system_model.value("dt_hr", time_step_duration)

        # initialize outputs
        total_power_out_timesteps = np.zeros(self.config.n_control_window)
        soc_timesteps = np.zeros(self.config.n_control_window)

        for t in range(len(storage_dispatch_commands)):
            # Set to 0.0 for each loop start
            self.unmet_demand = 0.0
            self.excess_resource = 0.0
            self.requested_electricity = storage_dispatch_commands[t]

            # Grab the available charge/discharge capacity of the battery
            P_chargeable = self.system_model.value("P_chargeable")

            # If discharging... electricity_in is the commanded electricity from dispatch,
            # accounting for demand, positive is charge and negative is discharge
            # if storage_dispatch_commands[t] > 0.0:
            #     # If the battery has been discharged to its minimum SOC level (with a tolerance)
            #     if (self.system_model.value("SOC") - self.system_model.value("minimum_SOC"))<0.05:
            #         # self.unmet_demand = storage_dispatch_commands[t]
            #         # Avoid trickle power by setting to 0.0
            #         storage_dispatch_commands[t] = 0.0

            # If charging...
            if storage_dispatch_commands[t] < 0.0:
                # If the input electricity magnitude is greater than the battery chargeable capacity
                if storage_dispatch_commands[t] < P_chargeable:
                    # Eliminates trickle power (~10-15 kW) when battery is fully charged
                    if P_chargeable > 0.0:
                        P_chargeable = 0.0

                    # Change the sign to indicate that a positive amount of power is being
                    # passed through the battery model
                    self.excess_resource = -1 * (storage_dispatch_commands[t] - P_chargeable)
                    # Limit the charging power to the available capacity of the battery
                    storage_dispatch_commands[t] = P_chargeable

            # Set the input variable to the desired value
            # import pdb; pdb.set_trace()
            self.system_model.value(control_variable, storage_dispatch_commands[t])

            # Simulate the PySAM BatteryStateful model
            self.system_model.execute(0)

            # save outputs
            total_power_out_timesteps[t] = self.system_model.value("P")
            soc_timesteps[t] = self.system_model.value("SOC")

            # This if statement is true when the battery is discharging and is unable to dispatch
            # the full amount of power required by the demand. It determines the remaining unmet
            # demand after the battery has discharged what is possible before hitting the battery's
            # minimum SOC level.
            # if self.requested_electricity >= 0.0:
            #     # If the desired discharge power is greater than the available battery power
            #     if (self.system_model.value("SOC") - self.system_model.value("minimum_SOC"))<0.05:
            #         # Unmet demand equals the demand minus the discharged power
            #         self.unmet_demand = self.requested_electricity - self.system_model.value("P")

            # Store outputs based on the outputs defined in `BatteryOutputs` above. The values are
            # scraped from the PySAM model modules `StatePack` and `StateCell`.
            for attr in self.outputs.stateful_attributes:
                if hasattr(self.system_model.StatePack, attr) or hasattr(
                    self.system_model.StateCell, attr
                ):
                    getattr(self.outputs, attr)[sim_start_index + t] = self.system_model.value(attr)

            for attr in self.outputs.component_attributes:
                getattr(self.outputs, attr)[sim_start_index + t] = getattr(self, attr)

        return total_power_out_timesteps, soc_timesteps

        # self.stateful_attributes = [
        #     "I",
        #     "P",
        #     "Q",
        #     "SOC",
        #     "T_batt",
        #     "n_cycles",
        #     "P_chargeable",
        #     "P_dischargeable",
        # ]

    def size_batterystateful(self, desired_capacity, desired_voltage, module_specs=None):
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
        if not isinstance(self.system_model, BatteryStateful.BatteryStateful):
            raise TypeError

        original_capacity = self.system_model.ParamsPack.nominal_energy

        self.system_model.ParamsPack.nominal_voltage = desired_voltage
        self.system_model.ParamsPack.nominal_energy = desired_capacity

        # calculate thermal
        thermal_inputs = {
            "mass": self.system_model.ParamsPack.mass,
            "surface_area": self.system_model.ParamsPack.surface_area,
            "original_capacity": original_capacity,
            "desired_capacity": desired_capacity,
        }
        if module_specs is not None:
            module_specs = {"module_" + k: v for k, v in module_specs.items()}
            thermal_inputs.update(module_specs)

        thermal_outputs = self.calculate_thermal_params(thermal_inputs)

        self.system_model.ParamsPack.mass = thermal_outputs["mass"]
        self.system_model.ParamsPack.surface_area = thermal_outputs["surface_area"]

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

        mass = input_dict["mass"]
        surface_area = input_dict["surface_area"]
        original_capacity = input_dict["original_capacity"]
        desired_capacity = input_dict["desired_capacity"]

        mass_per_specific_energy = mass / original_capacity

        volume = (surface_area / 6) ** (3 / 2)

        volume_per_specific_energy = volume / original_capacity

        output_dict = {
            "mass": mass_per_specific_energy * desired_capacity,
            "surface_area": (volume_per_specific_energy * desired_capacity) ** (2 / 3) * 6,
        }

        if input_dict.keys() >= {"module_capacity", "module_surface_area"}:
            module_capacity = input_dict["module_capacity"]
            module_surface_area = input_dict["module_surface_area"]
            output_dict["surface_area"] = module_surface_area * desired_capacity / module_capacity

        return output_dict

    def _set_control_mode(
        self,
        control_mode: float = 1.0,
        input_power: float = 0.0,
        input_current: float = 0.0,
        control_variable: str = "input_power",
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
