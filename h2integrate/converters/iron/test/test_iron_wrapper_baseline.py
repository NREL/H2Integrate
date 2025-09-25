import pytest
import openmdao.api as om
from pytest import fixture

from h2integrate import EXAMPLE_DIR
from h2integrate.core.inputs.validation import load_plant_yaml, load_driver_yaml
from h2integrate.converters.iron.iron_wrapper import IronComponent


@fixture
def baseline_iron_tech():
    iron_config = {
        "LCOE": 58.02,
        "LCOH": 7.10,
        "winning_type": "ng",
        "post_type": "none",
        "mine": "Northshore",
        "taconite_pellet_type": "drg",
        "win_capacity_denom": "iron",
        "iron_post_capacity": 1000000,
        "iron_win_capacity": 1418095,
        "ore_cf_estimate": 0.9,
        "cost_year": 2020,
    }
    return iron_config


@fixture
def plant_config():
    plant_config = load_plant_yaml(EXAMPLE_DIR / "20_iron_mn_to_il" / "plant_config.yaml")
    return plant_config


@fixture
def driver_config():
    driver_config = load_driver_yaml(EXAMPLE_DIR / "20_iron_mn_to_il" / "driver_config.yaml")
    return driver_config


def test_baseline_iron(plant_config, driver_config, baseline_iron_tech, subtests):
    test_cases = {
        "ng/none": {"winning_type": "ng", "post_type": "none"},
        "ng/eaf": {"winning_type": "ng", "post_type": "eaf"},
        "h2/none": {"winning_type": "h2", "post_type": "none"},
        "h2/eaf": {"winning_type": "h2", "post_type": "eaf"},
    }
    expected_lcoi = {
        "ng/none": 370.212190,  # USD/t
        "ng/eaf": 513.857475,
        "h2/none": 715.101542,
        "h2/eaf": 858.972702,
    }

    for test_name, test_inputs in test_cases.items():
        baseline_iron_tech.update(test_inputs)
        prob = om.Problem()
        comp = IronComponent(
            plant_config=plant_config,
            tech_config={"model_inputs": {"cost_parameters": baseline_iron_tech}},
            driver_config=driver_config,
        )
        prob.model.add_subsystem("iron", comp)
        prob.setup()
        prob.run_model()

        with subtests.test(f"baseline LCOI for {test_name}"):
            lcoi = prob.get_val("iron.LCOI", units="USD/t")
            assert pytest.approx(lcoi, rel=1e-3) == expected_lcoi[test_name]
