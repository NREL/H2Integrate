from copy import deepcopy
from pathlib import Path

import yaml
import numpy as np
import pytest
import openmdao.api as om
from openmdao.utils.assert_utils import assert_check_totals
import pyomo.environ as pyomo
from pyomo.util.check_units import assert_units_consistent

from h2integrate.core.h2integrate_model import H2IntegrateModel
from h2integrate.control.control_strategies.openloop_controllers import (
    DemandOpenLoopController,
    PassThroughOpenLoopController,
)
from h2integrate.storage.battery.pysam_battery import PySAMBatteryPerformanceModel
from h2integrate.control.control_strategies.pyomo_controllers import HeuristicLoadFollowingController
from h2integrate.control.control_rules.pyomo_control_options import PyomoControlOptions


def test_pass_through_controller(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the configuration files
    tech_config_path = current_dir / "inputs" / "tech_config.yaml"

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    # Set up the OpenMDAO problem
    prob = om.Problem()

    prob.model.add_subsystem(
        name="IVC",
        subsys=om.IndepVarComp(name="hydrogen_in", val=np.arange(10)),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        "pass_through_controller",
        PassThroughOpenLoopController(
            plant_config={}, tech_config=tech_config["technologies"]["h2_storage"]
        ),
        promotes=["*"],
    )

    prob.setup()

    prob.run_model()

    # Run the test
    with subtests.test("Check output"):
        assert pytest.approx(prob.get_val("hydrogen_out"), rel=1e-3) == np.arange(10)

    # Run the test
    with subtests.test("Check derivatives"):
        # check total derivatives using OpenMDAO's check_totals and assert tools
        assert_check_totals(
            prob.check_totals(
                of=[
                    "hydrogen_out",
                ],
                wrt=[
                    "hydrogen_in",
                ],
                step=1e-6,
                form="central",
                show_only_incorrect=False,
                out_stream=None,
            )
        )


def test_demand_controller(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the configuration files
    tech_config_path = current_dir / "inputs" / "tech_config.yaml"

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    tech_config["technologies"]["h2_storage"]["control_strategy"]["model"] = (
        "demand_openloop_controller"
    )
    tech_config["technologies"]["h2_storage"]["model_inputs"]["control_parameters"] = {
        "resource_name": "hydrogen",
        "resource_rate_units": "kg/h",
        "max_capacity": 10.0,  # kg
        "max_charge_percent": 1.0,  # percent as decimal
        "min_charge_percent": 0.0,  # percent as decimal
        "init_charge_percent": 1.0,  # percent as decimal
        "max_charge_rate": 1.0,  # kg/time step
        "max_discharge_rate": 0.5,  # kg/time step
        "charge_efficiency": 1.0,
        "discharge_efficiency": 1.0,
        "demand_profile": [1.0] * 10,  # Example: 10 time steps with 10 kg/time step demand
        "n_time_steps": 10,
    }

    # Set up the OpenMDAO problem
    prob = om.Problem()

    prob.model.add_subsystem(
        name="IVC",
        subsys=om.IndepVarComp(name="hydrogen_in", val=np.arange(10)),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        "demand_openloop_controller",
        DemandOpenLoopController(
            plant_config={}, tech_config=tech_config["technologies"]["h2_storage"]
        ),
        promotes=["*"],
    )

    prob.setup()

    prob.run_model()

    # Run the test
    with subtests.test("Check output"):
        assert pytest.approx([0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "hydrogen_out"
        )

    with subtests.test("Check curtailment"):
        assert pytest.approx([0.0, 0.0, 0.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]) == prob.get_val(
            "hydrogen_curtailed"
        )

    with subtests.test("Check soc"):
        assert pytest.approx([0.95, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "hydrogen_soc"
        )

    with subtests.test("Check missed load"):
        assert pytest.approx([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) == prob.get_val(
            "hydrogen_missed_load"
        )


def test_pyomo_controller(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the input files
    input_path = current_dir / "inputs" / "pyomo_controller" / "h2i_wind_to_h2_storage.yaml"

    model = H2IntegrateModel(input_path)

    model.run()

    prob = model.prob

    # Run the test
    with subtests.test("Check output"):
        assert pytest.approx([0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "h2_storage.hydrogen_out"
        )

    with subtests.test("Check curtailment"):
        assert pytest.approx([0.0, 0.0, 0.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]) == prob.get_val(
            "h2_storage.hydrogen_curtailed"
        )

    with subtests.test("Check soc"):
        assert pytest.approx([0.95, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "h2_storage.hydrogen_soc"
        )

    with subtests.test("Check missed load"):
        assert pytest.approx([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) == prob.get_val(
            "h2_storage.hydrogen_missed_load"
        )


def test_demand_controller_round_trip_efficiency(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the configuration files
    tech_config_path = current_dir / "inputs" / "tech_config.yaml"

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    tech_config["technologies"]["h2_storage"]["control_strategy"]["model"] = (
        "demand_openloop_controller"
    )
    tech_config["technologies"]["h2_storage"]["model_inputs"]["control_parameters"] = {
        "resource_name": "hydrogen",
        "resource_rate_units": "kg/h",
        "max_capacity": 10.0,  # kg
        "max_charge_percent": 1.0,  # percent as decimal
        "min_charge_percent": 0.0,  # percent as decimal
        "init_charge_percent": 1.0,  # percent as decimal
        "max_charge_rate": 1.0,  # kg/time step
        "max_discharge_rate": 0.5,  # kg/time step
        "charge_efficiency": 1.0,
        "discharge_efficiency": 1.0,
        "demand_profile": [1.0] * 10,  # Example: 10 time steps with 10 kg/time step demand
        "n_time_steps": 10,
    }

    tech_config_rte = deepcopy(tech_config)
    tech_config_rte["technologies"]["h2_storage"]["model_inputs"]["control_parameters"] = {
        "resource_name": "hydrogen",
        "resource_rate_units": "kg/h",
        "max_capacity": 10.0,  # kg
        "max_charge_percent": 1.0,  # percent as decimal
        "min_charge_percent": 0.0,  # percent as decimal
        "init_charge_percent": 1.0,  # percent as decimal
        "max_charge_rate": 1.0,  # kg/time step
        "max_discharge_rate": 0.5,  # kg/time step
        "round_trip_efficiency": 1.0,
        "demand_profile": [1.0] * 10,  # Example: 10 time steps with 10 kg/time step demand
        "n_time_steps": 10,
    }

    def set_up_and_run_problem(config):
        # Set up the OpenMDAO problem
        prob = om.Problem()

        prob.model.add_subsystem(
            name="IVC",
            subsys=om.IndepVarComp(name="hydrogen_in", val=np.arange(10)),
            promotes=["*"],
        )

        prob.model.add_subsystem(
            "demand_openloop_controller",
            DemandOpenLoopController(
                plant_config={}, tech_config=config["technologies"]["h2_storage"]
            ),
            promotes=["*"],
        )

        prob.setup()

        prob.run_model()

        return prob

    prob_ioe = set_up_and_run_problem(tech_config)
    prob_rte = set_up_and_run_problem(tech_config_rte)

    # Run the test
    with subtests.test("Check output"):
        assert pytest.approx(prob_ioe.get_val("hydrogen_out")) == prob_rte.get_val("hydrogen_out")

    with subtests.test("Check curtailment"):
        assert pytest.approx(prob_ioe.get_val("hydrogen_curtailed")) == prob_rte.get_val(
            "hydrogen_curtailed"
        )

    with subtests.test("Check soc"):
        assert pytest.approx(prob_ioe.get_val("hydrogen_soc")) == prob_rte.get_val("hydrogen_soc")

    with subtests.test("Check missed load"):
        assert pytest.approx(prob_ioe.get_val("hydrogen_missed_load")) == prob_rte.get_val(
            "hydrogen_missed_load"
        )


def test_heuristic_load_following_dispatch():
    dispatch_n_look_ahead = 48 # note this must be an even number for this test

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
    model = pyomo.ConcreteModel(name='battery_only')
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
                'include_lifecycle_count': False,
                'battery_dispatch': 'load_following_heuristic',
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
        dispatch_power[i] = battery.dispatch.storage_amount[i]
        assert battery.outputs.P[i] == pytest.approx(
            dispatch_power[i], 1E-3 * abs(dispatch_power[i])
        )

    # Check that the has non-zero charge and discharge power, and that the sum of charge
    # and discharge power are equal.
    assert sum(battery.dispatch.charge_resource) > 0.0
    assert sum(battery.dispatch.discharge_resource) > 0.0
    assert (sum(battery.dispatch.charge_resource) #* battery.dispatch.round_trip_efficiency / 100.0
            == pytest.approx(sum(battery.dispatch.discharge_resource)))

    # Check that the dispatch values have not changed
    expected_dispatch_power = np.concatenate(
        (np.ones(n_look_ahead_half) * -100., np.ones(n_look_ahead_half) * 100.)
    )
    np.testing.assert_allclose(dispatch_power, expected_dispatch_power)