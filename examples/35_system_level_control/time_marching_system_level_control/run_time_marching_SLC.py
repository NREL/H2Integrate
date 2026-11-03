import time
import pprint
from copy import deepcopy
from pathlib import Path

import yaml
import matplotlib.pyplot as plt

from h2integrate import H2IntegrateModel, load_tech_yaml, load_plant_yaml, load_driver_yaml
from h2integrate.core.dict_utils import percent_diff_dicts, find_nonzero_percent_diffs


# ANSI color codes
CRED = "\033[91m"
CGREEN = "\033[92m"
CYELLOW = "\033[93m"
CBLUE = "\033[94m"
CEND = "\033[0m"  # Resets the style back to normal


# Run one of both simulation paradigms by changing the flags in this dict
run_dict = {
    "run_sequential": True,
    "run_concurrent": True,
    # "run_sequential_opt": True,
    # "run_concurrent_opt": True,
}

# System level controller options

SLC_base = {
    "control_strategy": "DemandFollowingControl",
    "demand_component": "electrical_load_demand",
    "solver_options": {
        "solver_name": "gauss_seidel",
        "max_iter": 20,
        "convergence_tolerance": 1.0e-6,
    },
}


# - Cost minimiztion control
cost_minimization_config = deepcopy(SLC_base)
cost_minimization_config["control_strategy"] = "CostMinimizationControl"
# - Demand following control
demand_following_config = deepcopy(SLC_base)
demand_following_config["control_strategy"] = "DemandFollowingControl"
# - Profit maximization control
profit_maximization_config = deepcopy(SLC_base)
profit_maximization_config["control_strategy"] = "ProfitMaximizationControl"
profit_maximization_config["control_parameters"] = {
    "commodity_sell_price": 0.06,  # $/kWh default; overridden in run script
    "cost_per_tech": {
        "natural_gas_plant": "feedstock",  # use upstream feedstock (ng_feedstock) VarOpEx
        "grid_buy": "buy_price",  # use electricity_buy_price from cost config
    },
}


# Load config files into dict
config_root = Path(__file__).parent
config_path = config_root / "config.yaml"

# Load top level config
with Path(config_path).open() as f:
    config = yaml.safe_load(f)

config["driver_config"] = load_driver_yaml(config_root / config["driver_config"])
config["technology_config"] = load_tech_yaml(config_root / config["technology_config"])
config["plant_config"] = load_plant_yaml(config_root / config["plant_config"])


SLC_configs = {
    "demand_following": demand_following_config,
    "cost_minimization": cost_minimization_config,
    "profit_maximization": profit_maximization_config,
}

for k, v in SLC_configs.items():
    print(f"System level controller: {k}")
    config["plant_config"]["system_level_control"] = v

    fig, ax = plt.subplots(3, 1, sharex="all", layout="constrained")

    # Run simulation sequentially one subsystem at a time
    if run_dict.get("run_sequential", False):
        config_seq = deepcopy(config)
        config_seq["plant_config"]["plant"]["simulation"]["n_timesteps"] = 8760
        config_seq["plant_config"]["plant"]["simulation"]["n_timesteps_window"] = 8760

        # Create an H2I model for standard year-long simulation
        h2i_seq = H2IntegrateModel(config_seq)

        t0 = time.time()
        # Run the model
        h2i_seq.run()
        t1 = time.time()

        print("\n")
        print(CRED + str(type(h2i_seq.plant.system_level_controller)) + CEND)
        print("\n")

        print(f"Sequential took {t1 - t0:.3f} seconds")

        # Post-process the results
        h2i_seq.post_process(print_results=False)

        inputs_seq = dict(h2i_seq.model.list_inputs(out_stream=None))
        outputs_seq = dict(h2i_seq.model.list_outputs(out_stream=None))

        SLC_battery_cmd = outputs_seq[
            "plant.system_level_controller.battery_electricity_set_point"
        ]["val"]

        battery_out = outputs_seq[
            "plant.battery.StoragePerformanceModel.storage_electricity_discharge"
        ]["val"]
        battery_cmd = inputs_seq["plant.battery.StoragePerformanceModel.electricity_command_value"][
            "val"
        ]

        battery_SOC = outputs_seq["plant.battery.StoragePerformanceModel.SOC"]["val"]

        ax[0].plot(battery_SOC)
        ax[1].plot(battery_cmd)
        ax[2].plot(SLC_battery_cmd)

    # Run the simulation concurrently for all subsystems one step at a time
    if run_dict.get("run_concurrent", False):
        config_con = deepcopy(config)

        config_con["plant_config"]["plant"]["simulation"]["n_timesteps"] = 8760
        config_con["plant_config"]["plant"]["simulation"]["n_timesteps_window"] = 12

        # Create an H2I model for steppable simulation
        h2i_con = H2IntegrateModel(config_con)

        t0 = time.time()
        # Run the model

        h2i_con.run()

        t1 = time.time()

        print(f"Concurrent took {t1 - t0:.3f} seconds")

        print("\n")
        print(CRED + str(type(h2i_con.plant.system_level_controller)) + CEND)
        print("\n")

        # Post-process the results
        h2i_con.post_process(print_results=False)

        inputs_con = dict(h2i_con.model.list_inputs(out_stream=None))
        outputs_con = dict(h2i_con.model.list_outputs(out_stream=None))

        SLC_battery_cmd = outputs_con[
            "plant.system_level_controller.battery_electricity_set_point"
        ]["val"]

        battery_out = outputs_con[
            "plant.battery.StoragePerformanceModel.storage_electricity_discharge"
        ]["val"]
        battery_cmd = inputs_con["plant.battery.StoragePerformanceModel.electricity_command_value"][
            "val"
        ]

        battery_SOC = outputs_con["plant.battery.StoragePerformanceModel.SOC"]["val"]

        ax[0].plot(battery_SOC)
        ax[1].plot(battery_cmd)
        ax[2].plot(SLC_battery_cmd)

    ax[0].set_ylabel("Battery SOC")
    ax[1].set_ylabel("Battery command")
    ax[2].set_ylabel("SLC battery command")

    ax[0].axhline(40, color="black", linewidth=1)
    ax[0].axhline(60, color="black", linewidth=1)

    # ax[0].set_xlim([-5, 30])
    # ax[1].set_ylim([-12345.6, -12345.7])

    # Compare results
    if run_dict.get("run_sequential", False) and run_dict.get("run_concurrent", False):
        inputs_pd_dict = percent_diff_dicts(inputs_seq, inputs_con)
        outputs_pd_dict = percent_diff_dicts(outputs_seq, outputs_con)

        in_abs, in_rel = find_nonzero_percent_diffs(inputs_pd_dict, dict(inputs_seq))
        out_abs, out_rel = find_nonzero_percent_diffs(outputs_pd_dict, dict(outputs_seq))

        pprint.pprint(in_abs)
        pprint.pprint(out_abs)

        fig, ax = plt.subplots(4, 1, sharex="all", layout="constrained")

        ax[0].plot(
            inputs_seq[
                "plant.natural_gas_plant.NaturalGasPerformanceModel.electricity_command_value"
            ]["val"]
        )
        ax[0].plot(
            inputs_con[
                "plant.natural_gas_plant.NaturalGasPerformanceModel.electricity_command_value"
            ]["val"]
        )

        ax[1].plot(inputs_seq["plant.natural_gas_plant.controller.electricity_set_point"]["val"])
        ax[1].plot(inputs_con["plant.natural_gas_plant.controller.electricity_set_point"]["val"])

        ax[2].plot(
            outputs_seq["plant.natural_gas_plant.controller.electricity_command_value"]["val"]
        )
        ax[2].plot(
            outputs_con["plant.natural_gas_plant.controller.electricity_command_value"]["val"]
        )

        ax[3].plot(
            outputs_seq["plant.system_level_controller.natural_gas_plant_electricity_set_point"][
                "val"
            ]
        )
        ax[3].plot(
            outputs_con["plant.system_level_controller.natural_gas_plant_electricity_set_point"][
                "val"
            ]
        )

        print()

    if run_dict.get("run_sequential_opt", False) or run_dict.get("run_concurrent_opt", False):
        opt_params = {
            "driver": {
                "optimization": {
                    "flag": True,
                    "solver": "COBYLA",
                    "tol": 0.001,
                    "catol": 15000,
                    "max_iter": 100,
                    "rhobeg": 10,
                    "debug_print": True,
                }
            },
            "design_variables": {
                "battery": {
                    "storage_capacity": {
                        "flag": True,
                        "lower": 50000,
                        "upper": 100000,
                        "units": "kW*h",
                    }
                }
            },
            "objective": {
                "name": "plant.finance_subgroup_electricity.electricity_finance_profast_lco.LCOE"
            },
            "recorder": {
                "flag": True,
                "file": "wind_ng_demand_opt.sql",
                "includes": ["*"],
                "excludes": ["wind_resource.wind_resource_data"],
            },
        }

    if run_dict.get("run_sequential_opt", False):
        config_seq = deepcopy(config)
        config_seq["plant_config"]["plant"]["simulation"]["n_timesteps"] = 8760
        config_seq["plant_config"]["plant"]["simulation"]["n_timesteps_window"] = 8760

        config_seq["driver_config"].update(opt_params)

        # Create an H2I model for standard year-long simulation
        h2i_seq = H2IntegrateModel(config_seq)

        # Run the model
        h2i_seq.run()

        # Post-process the results
        h2i_seq.post_process(print_results=False)

    if run_dict.get("run_concurrent_opt", False):
        config_con = deepcopy(config)

        config_con["plant_config"]["plant"]["simulation"]["n_timesteps"] = 8760
        config_con["plant_config"]["plant"]["simulation"]["n_timesteps_window"] = 12

        config_con["driver_config"].update(opt_params)

        # Create an H2I model for steppable simulation
        h2i_con = H2IntegrateModel(config_con)

        # Run the model
        h2i_con.run()

        # Post-process the results
        h2i_con.post_process(print_results=False)
