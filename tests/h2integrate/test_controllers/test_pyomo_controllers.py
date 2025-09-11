from pathlib import Path

import yaml
import numpy as np
import pytest
import openmdao.api as om

from h2integrate.core.h2integrate_model import H2IntegrateModel
from h2integrate.storage.battery.pysam_battery import PySAMBatteryPerformanceModel
from h2integrate.storage.hydrogen.eco_storage import H2Storage
from h2integrate.control.control_rules.storage.battery import PyomoDispatchBattery
from h2integrate.control.control_rules.storage.h2_storage import PyomoDispatchH2Storage
from h2integrate.control.control_strategies.pyomo_controllers import (
    HeuristicLoadFollowingController,
)


def test_pyomo_h2storage_controller(subtests):
    # # Get the directory of the current script
    # current_dir = Path(__file__).parent

    # # Resolve the paths to the input files
    # input_path = current_dir / "inputs" / "pyomo_controller" / "h2i_wind_to_h2_storage.yaml"

    # model = H2IntegrateModel(input_path)

    # model.run()

    # prob = model.prob

    # # Run the test
    # with subtests.test("Check output"):
    #     assert pytest.approx([0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
    #         "h2_storage.hydrogen_out"
    #     )

    # with subtests.test("Check curtailment"):
    #     assert pytest.approx([0.0, 0.0, 0.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]) == prob.get_val(
    #         "h2_storage.hydrogen_excess_resource"
    #     )

    # with subtests.test("Check soc"):
    #     assert pytest.approx([0.95, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
    #         "h2_storage.hydrogen_soc"
    #     )

    # with subtests.test("Check missed load"):
    #     assert pytest.approx([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) == prob.get_val(
    #         "h2_storage.hydrogen_unmet_demand"
    #     )

    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Get the paths for the relevant input files
    plant_config_path = current_dir / "inputs" / "pyomo_h2_storage_controller" / "plant_config.yaml"
    tech_config_path = current_dir / "inputs" / "pyomo_h2_storage_controller" / "tech_config.yaml"

    # Load the plant configuration
    with plant_config_path.open() as file:
        plant_config = yaml.safe_load(file)

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    # Fabricate some oscillating power generation data: 0 kW for the first 12 hours, 10000 kW for
    # the second tweleve hours, and repeat that daily cycle over a year.
    n_look_ahead_half = int(24 / 2)

    hydrogen_in = np.concatenate(
        (np.ones(n_look_ahead_half) * 0, np.ones(n_look_ahead_half) * 1000)
    )
    hydrogen_in = np.tile(hydrogen_in, 365)

    demand_in = np.ones(8760) * 500.0

    # Setup the OpenMDAO problem and add subsystems
    prob = om.Problem()

    prob.model.add_subsystem(
        "pyomo_dispatch_h2_storage",
        PyomoDispatchH2Storage(
            plant_config=plant_config, tech_config=tech_config["technologies"]["h2_storage"]
        ),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        "h2_storage_heuristic_load_following_controller",
        HeuristicLoadFollowingController(
            plant_config=plant_config, tech_config=tech_config["technologies"]["h2_storage"]
        ),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        "h2_storage",
        H2Storage(
            plant_config=plant_config, tech_config=tech_config["technologies"]["h2_storage"]
        ),
        promotes=["*"],
    )

    # Setup the system and required values
    prob.setup()
    # prob.set_val("battery.control_variable", "input_power")
    prob.set_val("h2_storage.hydrogen_in", hydrogen_in)
    # prob.set_val("battery.demand_in", demand_in)

    # Run the model
    prob.run_model()


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
        5999.99995059,
        5990.56676743,
        5990.138959,
        5989.64831176,
        5989.08548217,
        5988.44193888,
        5987.70577962,
        5986.86071125,
        5985.88493352,
        5984.7496388,
        5983.41717191,
        5981.839478,
        6000.,
        6000.,
        6000.,
        6000.,
        6000.,
        6000.,
        6000.,
        6000.,
        6000.,
        6000.,
        6000.,
        6000.,
    ]

    expected_battery_electricity_out = [
        5999.99995059,
        5990.56676743,
        5990.138959,
        5989.64831176,
        5989.08548217,
        5988.44193888,
        5987.70577962,
        5986.86071125,
        5985.88493352,
        5984.7496388,
        5983.41717191,
        5981.839478,
        -3988.62235554,
        -3989.2357847,
        -3989.76832626,
        -3990.26170521,
        -3990.71676106,
        -3991.13573086,
        -3991.52143699,
        -3991.87684905,
        -3992.20485715,
        -3992.50815603,
        -3992.78920148,
        -3993.05020268,
    ]

    expected_SOC = [
        49.39724571,
        46.54631833,
        43.69133882,
        40.83119769,
        37.96394628,
        35.08762294,
        32.20015974,
        29.29919751,
        26.38184809,
        23.44436442,
        20.48162855,
        17.48627159,
        19.47067094,
        21.44466462,
        23.40741401,
        25.36052712,
        27.30530573,
        29.24281439,
        31.17393198,
        33.09939078,
        35.01980641,
        36.93570091,
        38.84752069,
        40.75565055,
    ]

    expected_unmet_demand_out = np.zeros(len(expected_SOC))
    expected_excess_resource_out = np.zeros(len(expected_SOC))

    with subtests.test("Check electricity_out"):
        assert (
            pytest.approx(expected_electricity_out) == prob.get_val("battery.electricity_out")[0:24]
        )
    
    with subtests.test("Check battery_electricity_out"):
        assert (
            pytest.approx(expected_battery_electricity_out) == prob.get_val(
                "battery.battery_electricity_out"
            )[0:24]
        )

    with subtests.test("Check SOC"):
        assert pytest.approx(expected_SOC) == prob.get_val("battery.SOC")[0:24]

    with subtests.test("Check unmet_demand"):
        assert (
            pytest.approx(expected_unmet_demand_out)
            == prob.get_val("battery.unmet_demand_out")[0:24]
        )

    with subtests.test("Check excess_resource_out"):
        assert (
            pytest.approx(expected_excess_resource_out)
            == prob.get_val("battery.excess_resource_out")[0:24]
        )

    # Test the case where the battery is discharged to its lower SOC limit
    electricity_in = np.zeros(8760)
    demand_in = np.ones(8760) * 30000

    # Setup the system and required values
    prob.setup()
    prob.set_val("battery.control_variable", "input_power")
    prob.set_val("battery.electricity_in", electricity_in)
    prob.set_val("battery.demand_in", demand_in)

    # Run the model
    prob.run_model()

    expected_electricity_out = [29999.99999999, 29930.56014218, 24790.59770946, 0., 0.]
    expected_battery_electricity_out = expected_electricity_out
    expected_SOC = [37.69010284, 22.89921133, 10.01660975, 10.01660975, 10.01660975]
    expected_unmet_demand_out = [0., 0., 5209.40229054, 30000., 30000.]
    expected_excess_resource_out = np.zeros(5)

    with subtests.test("Check electricity_out for min SOC"):
        assert (
            pytest.approx(expected_electricity_out) == prob.get_val("battery.electricity_out")[:5]
        )

    with subtests.test("Check battery_electricity_out for min SOC"):
        assert (
            pytest.approx(expected_battery_electricity_out) == prob.get_val(
                "battery.battery_electricity_out"
            )[:5]
        )

    with subtests.test("Check SOC for min SOC"):
        assert pytest.approx(expected_SOC) == prob.get_val("battery.SOC")[:5]

    with subtests.test("Check unmet_demand for min SOC"):
        assert (
            pytest.approx(expected_unmet_demand_out)
            == prob.get_val("battery.unmet_demand_out")[:5]
        )

    with subtests.test("Check excess_resource_out for min SOC"):
        assert (
            pytest.approx(expected_excess_resource_out)
            == prob.get_val("battery.excess_resource_out")[:5]
        )

    # Test the case where the battery is charged to its upper SOC limit
    electricity_in = np.ones(8760) * 30000.0
    demand_in = np.zeros(8760)

    # Setup the system and required values
    prob.setup()
    prob.set_val("battery.control_variable", "input_power")
    prob.set_val("battery.electricity_in", electricity_in)
    prob.set_val("battery.demand_in", demand_in)

    # Run the model
    prob.run_model()

    expected_electricity_out = [0., 0., 6150.14483911, 30000., 30000.]
    expected_battery_electricity_out = [-30000.00847705, -29973.58679681, -23310.54620182, 0., 0.]
    expected_SOC = [66.00200558, 79.43840635, 90., 90., 90.]
    expected_unmet_demand_out = np.zeros(5)
    expected_excess_resource_out = [0., 0., 6150.14483911, 30000., 30000.]

    with subtests.test("Check electricity_out for max SOC"):
        assert (
            pytest.approx(expected_electricity_out) == prob.get_val("battery.electricity_out")[:5]
        )

    with subtests.test("Check battery_electricity_out for max SOC"):
        assert (
            pytest.approx(expected_battery_electricity_out) == prob.get_val(
                "battery.battery_electricity_out"
            )[:5]
        )

    with subtests.test("Check SOC for max SOC"):
        assert pytest.approx(expected_SOC) == prob.get_val("battery.SOC")[:5]

    with subtests.test("Check unmet_demand for max SOC"):
        assert (
            pytest.approx(expected_unmet_demand_out)
            == prob.get_val("battery.unmet_demand_out")[:5]
        )

    with subtests.test("Check excess_resource_out for max SOC"):
        assert (
            pytest.approx(expected_excess_resource_out)
            == prob.get_val("battery.excess_resource_out")[:5]
        )
