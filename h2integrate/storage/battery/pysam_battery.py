from dataclasses import asdict, dataclass
from collections.abc import Sequence

import numpy as np
import PySAM.BatteryStateful as BatteryStateful
from attrs import field, define
from hopp.utilities.validators import gt_zero, contains, range_val

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
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
    Container for simulated outputs from the `BatteryStateful` and HOPP dispatch models.

    Attributes:
        I (Sequence): Battery current [A] per timestep.
        P (Sequence): Battery power [kW] per timestep.
        Q (Sequence): Battery capacity [Ah] per timestep.
        SOC (Sequence): State of charge [%] per timestep.
        T_batt (Sequence): Battery temperature [°C] per timestep.
        gen (Sequence): Generated power [kW] per timestep.
        n_cycles (Sequence): Cumulative rainflow cycles since start of simulation [1].
        P_chargeable (Sequence): Maximum estimated chargeable power [kW] per timestep.
        P_dischargeable (Sequence): Maximum estimated dischargeable power [kW] per timestep.

        dispatch_I (list[float]): Dispatch-model battery current [A] per timestep.
            Only applicable for dispatch models where current is modeled.
        dispatch_P (list[float]): Dispatch-model battery power [MW] per timestep.
        dispatch_SOC (list[float]): Dispatch-model state of charge [%] per timestep.
        dispatch_lifecycles_per_day (list[int | None]): Number of battery cycles per
            control window. Length is equal to the number of control windows.

        unmet_demand (list[float]): Unmet demand [kW] per timestep.
        excess_resource (list[float]): Excess available resource [kW] per timestep.
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
    """Configuration class for battery performance models.

    This class defines configuration parameters for simulating battery
    performance in either PySAM or HOPP system models. It includes
    specifications such as capacity, chemistry, state-of-charge limits,
    and reference module characteristics.

    Attributes:
        max_capacity (float):
            Maximum battery energy capacity in kilowatt-hours (kWh).
            Must be greater than zero.
        rated_commodity_capacity (float):
            Rated power capacity of the battery in kilowatts (kW).
            Must be greater than zero.
        system_model_source (str):
            Source software for the system model. Options are:
                - "pysam"
                - "hopp"
        chemistry (str):
            Battery chemistry option. Supported values include:
                - PySAM: "LFPGraphite", "LMOLTO", "LeadAcid", "NMCGraphite"
                - HOPP: "LDES" (generic long-duration energy storage)
        min_charge_percent (float):
            Minimum allowable state of charge as a fraction (0 to 1).
        max_charge_percent (float):
            Maximum allowable state of charge as a fraction (0 to 1).
        init_charge_percent (float):
            Initial state of charge as a fraction (0 to 1).
        n_timesteps (int, optional):
            Number of simulation timesteps. Defaults to 8760 (hourly for one year).
        dt (float, optional):
            Time step duration in hours. Defaults to 1.0.
        n_control_window (int, optional):
            Number of timesteps in the control window. Defaults to 24.
        n_horizon_window (int, optional):
            Number of timesteps in the horizon window. Defaults to 48.
        ref_module_capacity (int | float, optional):
            Reference module capacity in kilowatt-hours (kWh).
            Defaults to 400.
        ref_module_surface_area (int | float, optional):
            Reference module surface area in square meters (m²).
            Defaults to 30.
    """

    max_capacity: float = field(validator=gt_zero)
    rated_commodity_capacity: float = field(validator=gt_zero)

    system_model_source: str = field(validator=contains(["pysam", "hopp"]))
    chemistry: str = field(
        validator=contains(["LFPGraphite", "LMOLTO", "LeadAcid", "NMCGraphite", "LDES"]),
    )
    min_charge_percent: float = field(validator=range_val(0, 1))
    max_charge_percent: float = field(validator=range_val(0, 1))
    init_charge_percent: float = field(validator=range_val(0, 1))
    n_timesteps: int = field(default=8760)
    dt: float = field(default=1.0)
    n_control_window: int = field(default=24)
    n_horizon_window: int = field(default=48)
    ref_module_capacity: int | float = field(default=400)
    ref_module_surface_area: int | float = field(default=30)


class PySAMBatteryPerformanceModel(BatteryPerformanceBaseClass):
    """OpenMDAO component wrapping the PySAM Battery Performance model.

    This class integrates the NREL PySAM `BatteryStateful` model into
    an OpenMDAO component. It provides inputs and outputs for battery
    capacity, charge/discharge power, state of charge, and unmet or excess
    demand. The component can be used in standalone simulations or in
    dispatch optimization frameworks (e.g., Pyomo).

    Attributes:
        config (PySAMBatteryPerformanceModelConfig):
            Configuration parameters for the battery performance model.
        system_model (BatteryStateful):
            Instance of the PySAM BatteryStateful model, initialized with
            the selected chemistry and configuration parameters.
        outputs (BatteryOutputs):
            Container for simulation outputs such as SOC, chargeable/dischargeable
            power, unmet demand, and excess resources.
        unmet_demand (float):
            Tracks unmet demand during simulation (kW).
        excess_resource (float):
            Tracks excess resource during simulation (kW).

    Inputs:
        charge_rate (float):
            Battery charge rate in kilowatts per hour (kW).
        storage_capacity (float):
            Total energy storage capacity in kilowatt-hours (kWh).
        control_variable (str):
            Control mode for the PySAM battery, either ``"input_power"``
            or ``"input_current"``.
        demand_in (ndarray):
            Power demand time series (kW).
        electricity_in (ndarray):
            Commanded input electricity (kW), typically from dispatch.

    Outputs:
        P_chargeable (ndarray):
            Maximum chargeable power (kW).
        P_dischargeable (ndarray):
            Maximum dischargeable power (kW).
        unmet_demand_out (ndarray):
            Remaining unmet demand after discharge (kW/h).
        excess_resource_out (ndarray):
            Excess energy not absorbed by the battery (kW/h).
        electricity_out (ndarray):
            Supplied electricity from the battery to meet demand (kW).
        SOC (ndarray):
            Battery state of charge (%).
        battery_electricity_out (ndarray):
            Electricity output from the battery model (kW).

    Methods:
        setup():
            Defines model inputs, outputs, configuration, and connections
            to plant-level dispatch (if applicable).
        compute(inputs, outputs, discrete_inputs, discrete_outputs):
            Runs the PySAM BatteryStateful model for a simulation timestep,
            updating outputs such as SOC, charge/discharge limits, unmet
            demand, and excess resources.
        simulate(electricity_in, demand_in, time_step_duration, control_variable,
            sim_start_index=0):
            Simulates the battery behavior across timesteps using either
            input power or input current as control.
        size_batterystateful(desired_capacity, desired_voltage, module_specs=None):
            Sizes the PySAM battery model to match a desired capacity and voltage,
            optionally scaling thermal properties based on reference module specs.
        calculate_thermal_params(input_dict):
            Calculates mass and surface area of the scaled battery using
            specific energy ratios or reference module data.
        _set_control_mode(control_mode=1.0, input_power=0.0, input_current=0.0,
            control_variable="input_power"):
            Sets the battery control mode (power or current).

    Notes:
        - Default timestep is 1 hour (``dt=1.0``).
        - State of charge (SOC) bounds are set using the configuration's
          ``min_charge_percent`` and ``max_charge_percent``.
        - If a Pyomo dispatch solver is provided, the battery will simulate
          dispatch decisions using solver inputs.
    """

    def setup(self):
        """Set up the PySAM Battery Performance model in OpenMDAO.

        Initializes the configuration, defines inputs/outputs for OpenMDAO,
        and creates a `BatteryStateful` instance with the selected chemistry.
        If dispatch connections are specified, it also sets up a discrete
        input for Pyomo solver integration.
        """
        self.config = PySAMBatteryPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=False,
        )

        self.add_input(
            "charge_rate",
            val=self.config.rated_commodity_capacity,
            units="kW",
            desc="Battery charge rate",
        )

        self.add_input(
            "storage_capacity",
            val=self.config.max_capacity,
            units="kW*h",
            desc="Battery storage capacity",
        )

        BatteryPerformanceBaseClass.setup(self)

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
        """Run the PySAM Battery model for one simulation step.

        Configures the battery stateful model parameters (SOC limits, timestep,
        thermal properties, etc.), executes the simulation, and stores the
        results in OpenMDAO outputs.

        Args:
            inputs (dict):
                Continuous input values (e.g., electricity_in, demand_in).
            outputs (dict):
                Dictionary where model outputs (SOC, P_chargeable, unmet demand, etc.)
                are written.
            discrete_inputs (dict):
                Discrete inputs such as control mode or Pyomo solver.
            discrete_outputs (dict):
                Discrete outputs (unused in this component).
        """
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
        # BatteryTools.battery_model_sizing(
        #     self.system_model,
        #     self.config.rated_commodity_capacity,
        #     self.config.max_capacity,
        #     self.system_model.ParamsPack.nominal_voltage,
        #     module_specs=module_specs,
        # )
        self.system_model.ParamsPack.h = 20
        self.system_model.ParamsPack.Cp = 900
        self.system_model.ParamsCell.resistance = 0.001
        self.system_model.ParamsCell.C_rate = (
            inputs["charge_rate"][0] / inputs["storage_capacity"][0]
        )

        # Minimum set of parameters to set to get statefulBattery to work
        self._set_control_mode()

        self.system_model.value("input_current", 0.0)
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
            (
                total_power_out,
                battery_power_out,
                unmet_demand,
                excess_resource,
                soc,
            ) = dispatch(self.simulate, kwargs, inputs)

        else:
            # Simulate the battery with provided inputs and no controller
            total_power_out, soc = self.simulate(
                storage_dispatch_commands=inputs["electricity_in"],
                time_step_duration=self.config.dt,
                control_variable=discrete_inputs["control_variable"],
            )
            # TODO how to calculate? these are not being calculated
            unmet_demand = self.outputs.unmet_demand
            excess_resource = self.outputs.excess_resource
            battery_power_out = self.outputs.P

        outputs["unmet_demand_out"] = unmet_demand
        outputs["excess_resource_out"] = excess_resource
        outputs["battery_electricity_out"] = battery_power_out
        outputs["electricity_out"] = total_power_out
        outputs["SOC"] = soc
        outputs["P_chargeable"] = self.outputs.P_chargeable
        outputs["P_dischargeable"] = self.outputs.P_dischargeable

    def simulate(
        self,
        storage_dispatch_commands: list,
        time_step_duration: list,
        control_variable: str,
        sim_start_index: int = 0,
    ):
        """Simulate battery behavior over a series of timesteps.

        Iterates over input electricity values and demand to simulate charge
        and discharge behavior. Applies SOC bounds, unmet demand tracking,
        and excess resource calculations.

        Args:
            electricity_in (list[float]):
                Commanded power values from the dispatch algorithm (kW).
            demand_in (list[float]):
                Power demand for each timestep (kW).
            time_step_duration (list[float]):
                Duration of each timestep (hours).
            control_variable (str):
                Battery control mode, either ``"input_power"`` or ``"input_current"``.
            sim_start_index (int, optional):
                Index offset for writing outputs into arrays. Defaults to 0.
        """
        # Loop through the provided input power/current (decided by control_variable)
        self.system_model.value("dt_hr", time_step_duration)

        # initialize outputs
        storage_power_out_timesteps = np.zeros(self.config.n_control_window)
        soc_timesteps = np.zeros(self.config.n_control_window)

        # get constant battery parameters needed during all time steps
        soc_max = self.system_model.value("maximum_SOC") / 100.0
        soc_min = self.system_model.value("minimum_SOC") / 100.0

        for t in range(len(storage_dispatch_commands)):
            # get storage SOC at time t
            soc = self.system_model.value("SOC") / 100.0

            # get dispatch command value at time t
            dispatch_command_t = storage_dispatch_commands[t]

            # manually adjust the dispatch command based on SOC
            max_chargeable_0 = self.config.rated_commodity_capacity  # according to specs
            max_chargeable_1 = np.maximum(
                0, -self.system_model.value("P_chargeable")
            )  # according to simulation
            max_chargeable_2 = (
                (soc_max - soc) * self.config.max_capacity / self.config.dt
            )  # according to soc
            max_chargeable = np.min([max_chargeable_0, max_chargeable_1, max_chargeable_2])

            max_dischargeable_0 = self.config.rated_commodity_capacity  # according to specs
            max_dischargeable_1 = np.maximum(
                0, self.system_model.value("P_dischargeable")
            )  # according to simulation
            max_dischargeable_2 = (
                (soc - soc_min) * self.config.max_capacity / self.config.dt
            )  # according to soc
            max_dischargeable = np.min(
                [max_dischargeable_0, max_dischargeable_1, max_dischargeable_2]
            )

            if dispatch_command_t < -max_chargeable:
                dispatch_command_t = -max_chargeable

            if dispatch_command_t > max_dischargeable:
                dispatch_command_t = max_dischargeable

            # Set the input variable to the desired value
            self.system_model.value(control_variable, dispatch_command_t)

            # Simulate the PySAM BatteryStateful model
            self.system_model.execute(0)

            # save outputs
            storage_power_out_timesteps[t] = self.system_model.value("P")
            soc_timesteps[t] = self.system_model.value("SOC")

            # Store outputs based on the outputs defined in `BatteryOutputs` above. The values are
            # scraped from the PySAM model modules `StatePack` and `StateCell`.
            for attr in self.outputs.stateful_attributes:
                if hasattr(self.system_model.StatePack, attr) or hasattr(
                    self.system_model.StateCell, attr
                ):
                    getattr(self.outputs, attr)[sim_start_index + t] = self.system_model.value(attr)

            for attr in self.outputs.component_attributes:
                getattr(self.outputs, attr)[sim_start_index + t] = getattr(self, attr)

        return storage_power_out_timesteps, soc_timesteps

    def size_batterystateful(self, desired_capacity, desired_voltage, module_specs=None):
        """Resize the PySAM BatteryStateful model.

        Updates the battery nominal voltage and energy capacity. If
        reference module specifications are provided, thermal properties
        (mass and surface area) are scaled accordingly.

        Args:
            desired_capacity (float):
                Desired battery capacity (kWhAC if AC-connected, kWhDC otherwise).
            desired_voltage (float):
                Desired battery voltage (V).
            module_specs (dict, optional):
                Reference module specifications for scaling thermal properties.
                Expected keys:
                    - "capacity" (float): Module capacity (kWh).
                    - "surface_area" (float): Module surface area (m²).

        Returns:
            dict: Updated sizing parameters including thermal properties.
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
        """Calculate battery thermal parameters after resizing.

        Uses specific energy and volume scaling relationships, or provided
        module reference data, to calculate the new battery mass and surface
        area at the desired capacity.

        Args:
            input_dict (dict):
                Thermal and capacity parameters. Expected keys:
                    - "mass" (float): Mass of original battery (kg).
                    - "surface_area" (float): Surface area of original battery (m²).
                    - "original_capacity" (float): Original capacity (Wh).
                    - "desired_capacity" (float): New capacity (Wh).
                    - "module_capacity" (float, optional): Module capacity (Wh).
                    - "module_surface_area" (float, optional): Module surface area (m²).

        Returns:
            dict:
                Dictionary with updated thermal parameters:
                - "mass" (float): New battery mass (kg).
                - "surface_area" (float): New battery surface area (m²).
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
        """Set the control mode for the PySAM BatteryStateful model.

        Configures whether the battery operates in power-control or
        current-control mode and initializes input values.

        Args:
            control_mode (float, optional):
                Mode flag: ``1.0`` for power control, ``0.0`` for current control.
                Defaults to 1.0.
            input_power (float, optional):
                Initial power input (kW). Defaults to 0.0.
            input_current (float, optional):
                Initial current input (A). Defaults to 0.0.
            control_variable (str, optional):
                Control variable name, either ``"input_power"`` or ``"input_current"``.
                Defaults to "input_power".
        """
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
