from pathlib import Path

import pytest
import yaml
import numpy as np
import pyomo.environ as pyomo
from pyomo.util.check_units import assert_units_consistent
import openmdao.api as om

from h2integrate.core.h2integrate_model import H2IntegrateModel
from h2integrate.storage.battery.pysam_battery import PySAMBatteryPerformanceModel
from h2integrate.control.control_strategies.pyomo_controllers import HeuristicLoadFollowingController
from h2integrate.control.control_rules.storage.battery import PyomoDispatchBattery
from h2integrate.control.control_rules.pyomo_control_options import PyomoControlOptions



def test_pyomo_h2storage_controller(subtests):
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


def test_pyomo_battery_controller(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the input files
    input_path = current_dir / "inputs" / "pyomo_battery_controller" / "h2i_wind_to_battery_storage.yaml"

    model = H2IntegrateModel(input_path)

    model.run()

    prob = model.prob

    # Run the test
    with subtests.test("Check output"):
        assert pytest.approx([0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "battery.electricity_out"
        )

    # with subtests.test("Check curtailment"):
    #     assert pytest.approx([0.0, 0.0, 0.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]) == prob.get_val(
    #         "h2_storage.hydrogen_curtailed"
    #     )

    with subtests.test("Check soc"):
        assert pytest.approx([0.95, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "battery.SOC"
        )

    # with subtests.test("Check missed load"):
    #     assert pytest.approx([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) == prob.get_val(
    #         "h2_storage.hydrogen_missed_load"
    #     )


def test_heuristic_load_following_battery_dispatch(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Get the paths for the relevant input files
    plant_config_path = current_dir / "inputs" / "pyomo_battery_controller" / "plant_config.yaml"
    tech_config_path = current_dir / "inputs" / "pyomo_battery_controller" / "tech_config.yaml"

    # Load the plant configuration
    with plant_config_path.open() as file:
        plant_config = yaml.safe_load(file)

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    # Fabricate some oscillating power generation data: 0 kW for the first 12 hours, 10000 kW for
    # the second tweleve hours, and repeat that daily cycle over a year.
    n_look_ahead_half = int(24 / 2)

    electricity_in = np.concatenate(
        (np.ones(n_look_ahead_half) * 0, np.ones(n_look_ahead_half) * 10000)
    )
    electricity_in = np.tile(electricity_in, 365)

    demand_in = np.ones(8760) * 6000.0

    # Setup the OpenMDAO problem and add subsystems
    prob = om.Problem()

    prob.model.add_subsystem(
        "pyomo_dispatch_battery",
        PyomoDispatchBattery(
            plant_config=plant_config, tech_config=tech_config["technologies"]["battery"]
        ),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        "battery_heuristic_load_following_controller",
        HeuristicLoadFollowingController(
            plant_config=plant_config, tech_config=tech_config["technologies"]["battery"]
        ),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        "battery",
        PySAMBatteryPerformanceModel(
            plant_config=plant_config, tech_config=tech_config["technologies"]["battery"]
        ),
        promotes=["*"],
    )

    # Setup the system and required values
    prob.setup()
    prob.set_val("battery.control_variable", "input_power")
    prob.set_val("battery.electricity_in", electricity_in)
    prob.set_val("battery.demand_in", demand_in)

    # Run the model
    prob.run_model()

    # Test the case where the charging/discharging cycle remains within the max and min SOC limits
    # Check the expected outputs to actual outputs
    expected_electricity_out = [
        4999.9999773,   4992.25494845,  4991.96052468,  4991.63342844,
        4991.26824326,  4990.86174197,  4990.40961474,  4989.9060779,
        4989.34362595,  4988.7127164,   4988.00134222,  4987.19448497,
        -3990.28117657, -3990.74350753, -3991.15657479, -3991.53821247,
        -3991.89075935, -3992.21669848, -3992.51846132, -3992.7983355,
        -3993.05841673, -3993.3006006,  -3993.52658454, -3993.73788495,
    ]

    expected_SOC = [
        49.87479765, 47.50390223, 45.12932011, 42.75108798, 40.3682277,  37.9797332,
        35.58459541, 33.18174418, 30.76997461, 28.34786178, 25.91365422, 23.4651282,
        25.4168656,  27.36180226, 29.29938411, 31.23051435, 33.15594392, 35.07630244,
        36.99212221, 38.90385706, 40.81189705, 42.71658006, 44.61820098, 46.517019,
    ]

    expected_unmet_demand_out = np.zeros(len(expected_SOC))

    expected_excess_resource_out = np.zeros(len(expected_SOC))

    with subtests.test("Check electricity_out"):
        assert pytest.approx(expected_electricity_out) == prob.get_val(
            "battery.electricity_out"
        )[0:24]

    with subtests.test("Check SOC"):
        assert pytest.approx(expected_SOC) == prob.get_val("battery.SOC")[0:24]

    with subtests.test("Check unmet_demand"):
        assert pytest.approx(expected_unmet_demand_out) == prob.get_val("battery.unmet_demand_out")[0:24]

    with subtests.test("Check excess_resource_out"):
        assert pytest.approx(expected_excess_resource_out) == prob.get_val(
            "battery.excess_resource_out"
        )[0:24]

    # Test the case where the battery is discharged to its lower SOC limit
    electricity_in = np.zeros(8760)

    # Setup the system and required values
    prob.setup()
    prob.set_val("battery.control_variable", "input_power")
    prob.set_val("battery.electricity_in", electricity_in)
    prob.set_val("battery.demand_in", demand_in)

    # Run the model
    prob.run_model()

    expected_electricity_out = np.zeros(24)
    expected_SOC = np.ones(24) * 10.00158898
    expected_unmet_demand_out = np.ones(24) * 6000.0
    expected_excess_resource_out = np.zeros(24)

    with subtests.test("Check electricity_out"):
        assert pytest.approx(expected_electricity_out) == prob.get_val(
            "battery.electricity_out"
        )[-24:]

    with subtests.test("Check SOC"):
        assert pytest.approx(expected_SOC) == prob.get_val("battery.SOC")[-24:]

    with subtests.test("Check unmet_demand"):
        assert pytest.approx(expected_unmet_demand_out) == prob.get_val("battery.unmet_demand_out")[-24:]

    with subtests.test("Check excess_resource_out"):
        assert pytest.approx(expected_excess_resource_out) == prob.get_val(
            "battery.excess_resource_out"
        )[-24:]

    # Test the case where the battery is charged to its upper SOC limit
    electricity_in = np.ones(8760) * 10000.0

    # Setup the system and required values
    prob.setup()
    prob.set_val("battery.control_variable", "input_power")
    prob.set_val("battery.electricity_in", electricity_in)
    prob.set_val("battery.demand_in", demand_in)

    # Run the model
    prob.run_model()

    expected_electricity_out = np.zeros(24)
    expected_SOC = [
        90.65332934, 90.65361024, 90.65389112, 90.654172,   90.65445286, 90.65473371,
        90.65501454, 90.65529537, 90.65557618, 90.65585698, 90.65613777, 90.65641854,
        90.6566993,  90.65698005, 90.65726079, 90.65754151, 90.65782223, 90.65810293,
        90.65838361, 90.65866429, 90.65894495, 90.6592256,  90.65950624, 90.65978686,
    ]
    expected_unmet_demand_out = np.zeros(24)
    expected_excess_resource_out = np.ones(24) * 4000.0

    with subtests.test("Check electricity_out"):
        assert pytest.approx(expected_electricity_out) == prob.get_val(
            "battery.electricity_out"
        )[-24:]

    with subtests.test("Check SOC"):
        assert pytest.approx(expected_SOC) == prob.get_val("battery.SOC")[-24:]

    with subtests.test("Check unmet_demand"):
        assert pytest.approx(expected_unmet_demand_out) == prob.get_val("battery.unmet_demand_out")[-24:]

    with subtests.test("Check excess_resource_out"):
        assert pytest.approx(expected_excess_resource_out) == prob.get_val(
            "battery.excess_resource_out"
        )[-24:]


