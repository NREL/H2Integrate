from copy import deepcopy
from pathlib import Path

import yaml
import numpy as np
import pytest
import openmdao.api as om

from h2integrate.storage.battery.pysam_battery import (
    PySAMBatteryPerformanceModel,
    PySAMBatteryPerformanceModelConfig,
)


def test_pysam_battery_performance_model(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the configuration files
    tech_config_path = current_dir / "inputs" / "tech_config.yaml"

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    # Set up the OpenMDAO problem
    prob = om.Problem()

    n_control_window = tech_config["technologies"]["battery"]["model_inputs"]["shared_parameters"][
        "n_control_window"
    ]

    electricity_in = np.concatenate(
        (np.ones(int(n_control_window / 2)) * 1000.0, np.ones(int(n_control_window / 2)) * -1000.0)
    )

    prob.model.add_subsystem(
        name="IVC1",
        subsys=om.IndepVarComp(name="electricity_in", val=electricity_in, units="kW"),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        name="IVC2",
        subsys=om.IndepVarComp(name="time_step_duration", val=np.ones(n_control_window), units="h"),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        "pysam_battery",
        PySAMBatteryPerformanceModel(
            plant_config={}, tech_config=tech_config["technologies"]["battery"]
        ),
        promotes=["*"],
    )

    prob.setup()

    prob.set_val("control_variable", "input_power")

    prob.run_model()

    expected_battery_power = np.array(
        [
            999.99999997,
            998.57930115,
            998.52941043,
            998.51660931,
            998.50470535,
            998.49284335,
            998.48088314,
            998.46877688,
            998.45650206,
            998.44404534,
            998.43139721,
            998.41854985,
            -998.43134064,
            -998.44395855,
            -998.45637556,
            -998.46859632,
            -998.48062549,
            -998.49246743,
            -998.50412641,
            -998.51560657,
            -998.52691193,
            -998.53804633,
            -998.54901366,
            -998.55981744,
        ]
    )

    expected_battery_SOC = np.array(
        [
            51.70824047,
            51.30394294,
            50.8392576,
            50.37162579,
            49.90280372,
            49.43320374,
            48.96300622,
            48.49230981,
            48.02117569,
            47.54964497,
            47.0777468,
            46.60550259,
            47.08170333,
            47.55772227,
            48.03356641,
            48.50924213,
            48.98475532,
            49.46011143,
            49.93531553,
            50.41037238,
            50.88528642,
            51.36006186,
            51.83470268,
            52.30921264,
        ]
    )

    with subtests.test("expected_battery_power"):
        np.testing.assert_allclose(
            prob.get_val("battery_electricity_out"), expected_battery_power, rtol=1e-2
        )

    with subtests.test("expected_battery_SOC"):
        np.testing.assert_allclose(prob.get_val("SOC"), expected_battery_SOC, rtol=1e-2)


def test_battery_config(subtests):
    batt_kw = 5e3
    config_data = {
        "max_capacity": batt_kw * 4,
        "rated_commodity_capacity": batt_kw,
        "chemistry": "LFPGraphite",
        "init_charge_percent": 0.1,
        "max_charge_percent": 0.9,
        "min_charge_percent": 0.1,
        "system_model_source": "pysam",
    }

    config = PySAMBatteryPerformanceModelConfig.from_dict(config_data)

    with subtests.test("with minimal params batt_kw"):
        assert config.rated_commodity_capacity == batt_kw
    with subtests.test("with minimal params system_capacity_kwh"):
        assert config.max_capacity == batt_kw * 4
    with subtests.test("with minimal params minimum_SOC"):
        assert (
            config.min_charge_percent == 0.1
        )  # Decimal percent as compared to test_battery.py in HOPP 10%
    with subtests.test("with minimal params maximum_SOC"):
        assert (
            config.max_charge_percent == 0.9
        )  # Decimal percent as compared to test_battery.py in HOPP 90%
    with subtests.test("with minimal params initial_SOC"):
        assert (
            config.init_charge_percent == 0.1
        )  # Decimal percent as compared to test_battery.py in HOPP 10%
    with subtests.test("with minimal params system_model_source"):
        assert config.system_model_source == "pysam"
    with subtests.test("with minimal params n_timesteps"):
        assert config.n_timesteps == 8760
    with subtests.test("with minimal params dt"):
        assert config.dt == 1.0
    with subtests.test("with minimal params n_control_window"):
        assert config.n_control_window == 24
    with subtests.test("with minimal params n_horizon_window"):
        assert config.n_horizon_window == 48

    with subtests.test("with invalid capacity"):
        with pytest.raises(ValueError):
            data = deepcopy(config_data)
            data["rated_commodity_capacity"] = -1.0
            PySAMBatteryPerformanceModelConfig.from_dict(data)

        with pytest.raises(ValueError):
            data = deepcopy(config_data)
            data["max_capacity"] = -1.0
            PySAMBatteryPerformanceModelConfig.from_dict(data)

    with subtests.test("with invalid SOC"):
        # SOC values must be between 0-100
        with pytest.raises(ValueError):
            data = deepcopy(config_data)
            data["min_charge_percent"] = -1.0
            PySAMBatteryPerformanceModelConfig.from_dict(data)

        with pytest.raises(ValueError):
            data = deepcopy(config_data)
            data["max_charge_percent"] = 120.0
            PySAMBatteryPerformanceModelConfig.from_dict(data)

        with pytest.raises(ValueError):
            data = deepcopy(config_data)
            data["init_charge_percent"] = 120.0
            PySAMBatteryPerformanceModelConfig.from_dict(data)


def test_battery_initialization(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the configuration files
    tech_config_path = current_dir / "inputs" / "tech_config.yaml"

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    battery = PySAMBatteryPerformanceModel(
        plant_config={}, tech_config=tech_config["technologies"]["battery"]
    )

    battery.setup()

    with subtests.test("battery attribute not None system_model"):
        assert battery.system_model is not None
    with subtests.test("battery attribute not None outputs"):
        assert battery.outputs is not None

    with subtests.test("battery mass"):
        # this test value does not match the value in test_battery.py in HOPP
        # this is because the mass is computed in compute function in H2I
        # and in HOPP it's in the attrs_post_init function
        # suggest removing this subtest
        assert battery.system_model.ParamsPack.mass * 20000 == pytest.approx(3044540.0, 1e-3)
