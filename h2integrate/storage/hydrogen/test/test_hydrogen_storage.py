import numpy as np
import pytest
import openmdao.api as om
from pytest import fixture

from h2integrate.storage.hydrogen.h2_storage_cost import (
    PipeStorageCostModel,
    SaltCavernStorageCostModel,
    LinedRockCavernStorageCostModel,
)


@fixture
def plant_config():
    plant_config_dict = {
        "plant": {
            "plant_life": 30,
            "simulation": {
                "n_timesteps": 8760,  # Default number of timesteps for the simulation
            },
        },
    }
    return plant_config_dict


def test_salt_cavern_ex_2(plant_config, subtests):
    tech_config_dict = {
        "model_inputs": {
            "shared_parameters": {
                "max_capacity": 3580383.39133725,
                "max_charge_rate": 12549.62622698,
            }
        }
    }
    prob = om.Problem()
    comp = SaltCavernStorageCostModel(
        plant_config=plant_config,
        tech_config=tech_config_dict,
        driver_config={},
    )
    prob.model.add_subsystem("sys", comp)
    prob.setup()
    prob.run_model()

    with subtests.test("CapEx"):
        assert pytest.approx(prob.get_val("sys.CapEx")[0], rel=1e-6) == 65337437.17944019
    with subtests.test("OpEx"):
        assert pytest.approx(prob.get_val("sys.OpEx")[0], rel=1e-6) == 2358794.1150327
    with subtests.test("VarOpEx"):
        assert pytest.approx(np.sum(prob.get_val("sys.VarOpEx")), rel=1e-6) == 0.0
    with subtests.test("Cost year"):
        assert prob.get_val("sys.cost_year") == 2018


def test_lined_rock_cavern_ex_12_small_case(plant_config, subtests):
    tech_config_dict = {
        "model_inputs": {
            "shared_parameters": {
                "max_capacity": 169320.79994693,
                "max_charge_rate": 1568.70894716,
            }
        }
    }
    prob = om.Problem()

    comp = LinedRockCavernStorageCostModel(
        plant_config=plant_config,
        tech_config=tech_config_dict,
        driver_config={},
    )
    prob.model.add_subsystem("sys", comp)
    prob.setup()
    prob.run_model()

    with subtests.test("CapEx"):
        assert pytest.approx(prob.get_val("sys.CapEx")[0], rel=1e-6) == 18693728.23242369
    with subtests.test("OpEx"):
        assert pytest.approx(prob.get_val("sys.OpEx")[0], rel=1e-6) == 767466.36227705
    with subtests.test("VarOpEx"):
        assert pytest.approx(np.sum(prob.get_val("sys.VarOpEx")), rel=1e-6) == 0.0
    with subtests.test("Cost year"):
        assert prob.get_val("sys.cost_year") == 2018


def test_lined_rock_cavern_ex_1(plant_config, subtests):
    tech_config_dict = {
        "model_inputs": {
            "shared_parameters": {
                "max_capacity": 2081385.93267781,
                "max_charge_rate": 14118.14678877,
            }
        }
    }
    prob = om.Problem()
    comp = LinedRockCavernStorageCostModel(
        plant_config=plant_config,
        tech_config=tech_config_dict,
        driver_config={},
    )
    prob.model.add_subsystem("sys", comp)
    prob.setup()
    prob.run_model()

    with subtests.test("CapEx"):
        assert pytest.approx(prob.get_val("sys.CapEx")[0], rel=1e-6) == 92392496.03198986
    with subtests.test("OpEx"):
        assert pytest.approx(prob.get_val("sys.OpEx")[0], rel=1e-6) == 3228373.63748516
    with subtests.test("VarOpEx"):
        assert pytest.approx(np.sum(prob.get_val("sys.VarOpEx")), rel=1e-6) == 0.0
    with subtests.test("Cost year"):
        assert prob.get_val("sys.cost_year") == 2018


def test_lined_rock_cavern_ex_14(plant_config, subtests):
    tech_config_dict = {
        "model_inputs": {
            "shared_parameters": {
                "max_capacity": 2987042.0,
                "max_charge_rate": 12446.00729773,
            }
        }
    }
    prob = om.Problem()
    comp = LinedRockCavernStorageCostModel(
        plant_config=plant_config,
        tech_config=tech_config_dict,
        driver_config={},
    )
    prob.model.add_subsystem("sys", comp)
    prob.setup()
    prob.run_model()

    with subtests.test("CapEx"):
        assert pytest.approx(prob.get_val("sys.CapEx")[0], rel=1e-6) == 1.28437699 * 1e8
    with subtests.test("OpEx"):
        assert pytest.approx(prob.get_val("sys.OpEx")[0], rel=1e-6) == 4330693.49125131
    with subtests.test("VarOpEx"):
        assert pytest.approx(np.sum(prob.get_val("sys.VarOpEx")), rel=1e-6) == 0.0
    with subtests.test("Cost year"):
        assert prob.get_val("sys.cost_year") == 2018


def test_buried_pipe_storage(plant_config, subtests):
    tech_config_dict = {
        "model_inputs": {
            "shared_parameters": {
                "max_capacity": 3580383.39133725,
                "max_charge_rate": 12549.62622698,
            }
        }
    }
    prob = om.Problem()
    comp = PipeStorageCostModel(
        plant_config=plant_config,
        tech_config=tech_config_dict,
        driver_config={},
    )
    prob.model.add_subsystem("sys", comp)
    prob.setup()
    prob.run_model()

    with subtests.test("CapEx"):
        assert pytest.approx(prob.get_val("sys.CapEx")[0], rel=1e-6) == 1827170156.1390543
    with subtests.test("OpEx"):
        assert pytest.approx(prob.get_val("sys.OpEx")[0], rel=1e-6) == 56972128.44322313
    with subtests.test("VarOpEx"):
        assert pytest.approx(np.sum(prob.get_val("sys.VarOpEx")), rel=1e-6) == 0.0
    with subtests.test("Cost year"):
        assert prob.get_val("sys.cost_year") == 2018
