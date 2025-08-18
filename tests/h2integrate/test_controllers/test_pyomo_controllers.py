from pathlib import Path

import yaml
import numpy as np
import pytest
import pyomo.environ as pyomo
from pyomo.util.check_units import assert_units_consistent

from h2integrate.storage.battery.pysam_battery import PySAMBatteryPerformanceModel
from h2integrate.control.control_rules.pyomo_control_options import PyomoControlOptions
from h2integrate.control.control_strategies.pyomo_controllers import (
    HeuristicLoadFollowingController,
)


def test_heuristic_load_following_dispatch(subtests):
    dispatch_n_look_ahead = 48  # note this must be an even number for this test

    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the configuration files
    tech_config_path = current_dir / "inputs" / "tech_config_heuristic.yaml"

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    # Set up the OpenMDAO problem
    # prob = om.Problem()

    # prob.model.add_subsystem(
    #     name="IVC",
    #     subsys=om.IndepVarComp(name="electricity_demand_in", val=np.arange(10)),
    #     promotes=["*"],
    # )

    # prob.model.add_subsystem(
    #     "pass_through_controller",
    #     HeuristicLoadFollowingController(
    #         plant_config={}, tech_config=tech_config["technologies"]["battery"]
    #     ),
    #     promotes=["*"],
    # )

    battery = PySAMBatteryPerformanceModel(
        plant_config={}, tech_config=tech_config["technologies"]["battery"]
    )
    battery.setup()

    # Create pyomo model
    model = pyomo.ConcreteModel(name="battery_only")
    model.forecast_horizon = pyomo.Set(initialize=range(dispatch_n_look_ahead))

    # Instantiate battery dispatch
    battery.dispatch = HeuristicLoadFollowingController(
        plant_config={}, tech_config=tech_config["technologies"]["battery"]
    )
    battery.dispatch.setup(
        pyomo_model=model,
        index_set=model.forecast_horizon,
        system_model=battery.system_model,
        block_set_name="heuristic_load_following_battery",
        control_options=PyomoControlOptions(
            {
                "include_lifecycle_count": False,
                "battery_dispatch": "load_following_heuristic",
            }
        ),
    )

    # Setup dispatch for battery
    battery.dispatch.initialize_parameters()
    battery.dispatch.update_time_series_parameters(0)
    # Set initial SOC to minimum
    battery.dispatch.update_dispatch_initial_soc(battery.dispatch.minimum_soc)
    assert_units_consistent(model)

    # Generate test data for n horizon, charging for first half of the horizon,
    # then discharging for the latter half.
    tot_gen = np.ones(dispatch_n_look_ahead) * 1000
    n_look_ahead_half = int(dispatch_n_look_ahead / 2)
    grid_limit = np.concatenate(
        (np.ones(n_look_ahead_half) * 900, np.ones(n_look_ahead_half) * 1100)
    )

    # Set the dispatch pyomo variables
    battery.dispatch.set_fixed_dispatch(tot_gen, grid_limit, grid_limit)

    # Simulate the battery with the heuristic dispatch
    battery.battery_simulate_with_dispatch(n_periods=dispatch_n_look_ahead, sim_start_time=0)

    # Check that the power is being assigned correctly to the battery outputs
    dispatch_power = np.empty(dispatch_n_look_ahead)
    for i in range(dispatch_n_look_ahead):
        with subtests.test(f"Check dispatch[{i}]"):
            dispatch_power[i] = battery.dispatch.storage_amount[i]
            assert battery.outputs.P[i] == pytest.approx(
                dispatch_power[i], 1e-3 * abs(dispatch_power[i])
            )

    # Check that the has non-zero charge and discharge power, and that the sum of charge
    # and discharge power are equal.
    with subtests.test("charge_resource"):
        assert sum(battery.dispatch.charge_resource) > 0.0

    with subtests.test("discharge_resource"):
        assert sum(battery.dispatch.discharge_resource) > 0.0

    with subtests.test("charge_resource equals discharge_resource"):
        assert (
            sum(
                battery.dispatch.charge_resource
            )  # * battery.dispatch.round_trip_efficiency / 100.0
            == pytest.approx(sum(battery.dispatch.discharge_resource))
        )

    # Check that the dispatch values have not changed

    with subtests.test("expected_dispatch_power"):
        expected_dispatch_power = np.concatenate(
            (np.ones(n_look_ahead_half) * -100.0, np.ones(n_look_ahead_half) * 100.0)
        )
        np.testing.assert_allclose(dispatch_power, expected_dispatch_power)
