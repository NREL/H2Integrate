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

    grid_limit = np.concatenate(
        (np.ones(n_look_ahead_half) * 0, np.ones(n_look_ahead_half) * 10000)
    )
    grid_limit = np.tile(grid_limit, 365)

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
    prob.set_val("battery.electricity_in", grid_limit)

    # Run the model
    prob.run_model()

    # Check the expected outputs to actual outputs
    expected_electricity_out = [
        4.99999998e+03,  4.99246204e+03,  4.99196917e+03,  4.99163634e+03,
        4.99126979e+03,  4.99086267e+03,  4.99041021e+03,  4.98990645e+03,
        4.98934385e+03,  4.98871283e+03,  4.98800137e+03,  4.98719445e+03,
        -3.99028109e+03, -3.99074342e+03, -3.99115649e+03, -3.99153813e+03,
        -3.99189067e+03, -3.99221661e+03, -3.99251838e+03, -3.99279825e+03,
        -3.99305834e+03, -3.99330052e+03, -3.99352651e+03, -3.99373781e+03,
    ]

    expected_SOC = [
        49.80897816, 47.49611312, 45.12415453, 42.74694762, 40.36471502, 37.97666855,
        35.58187831, 33.17931145, 30.76778337, 28.34588133, 25.9118617,  23.463506,
        25.41518112, 27.36005981, 29.29758781, 31.22866815, 33.15405158, 35.07436754,
        36.99014816, 38.9018471,  40.80985428, 42.71450741, 44.61610126, 46.51489486,
    ]

    with subtests.test("Check electricity_out"):
        assert pytest.approx(expected_electricity_out) == prob.get_val(
            "battery.electricity_out"
        )[0:24]

    with subtests.test("Check SOC"):
        assert pytest.approx(expected_SOC) == prob.get_val("battery.SOC")[0:24]
