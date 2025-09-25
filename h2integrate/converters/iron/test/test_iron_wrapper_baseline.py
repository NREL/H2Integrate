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
def mine_iron_tech():
    iron_config = {
        "LCOE": 58.02,
        "LCOH": 7.10,
        "winning_type": "ng",
        "post_type": "none",
        "mine": "Hibbing",
        "taconite_pellet_type": "drg",
        "win_capacity_denom": "iron",
        "iron_post_capacity": 1000000,
        "iron_win_capacity": 1418095,
        "ore_cf_estimate": 0.9,
        "cost_year": 2020,
    }
    return iron_config


@fixture
def lcoe50_iron_tech():
    iron_config = {
        "LCOE": 50.0,
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
def lcoh6_iron_tech():
    iron_config = {
        "LCOE": 58.02,
        "LCOH": 6.00,
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
def lcoh3_iron_tech():
    iron_config = {
        "LCOE": 58.02,
        "LCOH": 3.00,
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
        "ng/none": 370.212189551055,  # USD/t
        "ng/eaf": 513.8574754088993,
        "h2/none": 715.1015416039348,
        "h2/eaf": 858.9727023405763,
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
            assert pytest.approx(lcoi, abs=0.3) == expected_lcoi[test_name]


def test_changing_mine_iron(plant_config, driver_config, mine_iron_tech, subtests):
    test_cases = {
        "ng/none": {"winning_type": "ng", "post_type": "none"},
        "ng/eaf": {"winning_type": "ng", "post_type": "eaf"},
        "h2/none": {"winning_type": "h2", "post_type": "none"},
        "h2/eaf": {"winning_type": "h2", "post_type": "eaf"},
    }
    expected_lcoi = {
        "ng/none": 354.77730320952014,
        "ng/eaf": 498.42258906736447,
        "h2/none": 699.666052372724,
        "h2/eaf": 843.5372131093657,
    }
    for test_name, test_inputs in test_cases.items():
        mine_iron_tech.update(test_inputs)
        prob = om.Problem()
        comp = IronComponent(
            plant_config=plant_config,
            tech_config={"model_inputs": {"cost_parameters": mine_iron_tech}},
            driver_config=driver_config,
        )
        prob.model.add_subsystem("iron", comp)
        prob.setup()
        prob.run_model()

        with subtests.test(f"Hibbing mine LCOI for {test_name}"):
            lcoi = prob.get_val("iron.LCOI", units="USD/t")
            assert pytest.approx(lcoi, abs=0.3) == expected_lcoi[test_name]


def test_lcoe50_iron(plant_config, driver_config, lcoe50_iron_tech, subtests):
    test_cases = {
        "ng/none": {"winning_type": "ng", "post_type": "none"},
        "ng/eaf": {"winning_type": "ng", "post_type": "eaf"},
        "h2/none": {"winning_type": "h2", "post_type": "none"},
        "h2/eaf": {"winning_type": "h2", "post_type": "eaf"},
    }

    expected_lcoi = {
        "ng/none": 369.07934010565174,
        "ng/eaf": 509.8866655496638,
        "h2/none": 714.305073437314,
        "h2/eaf": 855.2282058088431,
    }
    for test_name, test_inputs in test_cases.items():
        lcoe50_iron_tech.update(test_inputs)
        prob = om.Problem()
        comp = IronComponent(
            plant_config=plant_config,
            tech_config={"model_inputs": {"cost_parameters": lcoe50_iron_tech}},
            driver_config=driver_config,
        )
        prob.model.add_subsystem("iron", comp)
        prob.setup()
        prob.run_model()

        with subtests.test(f"Hibbing mine LCOI for {test_name}"):
            lcoi = prob.get_val("iron.LCOI", units="USD/t")
            assert pytest.approx(lcoi, abs=0.3) == expected_lcoi[test_name]


def test_lcoh6_iron(plant_config, driver_config, lcoh6_iron_tech, subtests):
    test_cases = {
        "ng/none": {"winning_type": "ng", "post_type": "none"},
        "ng/eaf": {"winning_type": "ng", "post_type": "eaf"},
        "h2/none": {"winning_type": "h2", "post_type": "none"},
        "h2/eaf": {"winning_type": "h2", "post_type": "eaf"},
    }

    expected_lcoi = {
        "ng/none": 370.212189551055,
        "ng/eaf": 513.8574754088993,
        "h2/none": 653.4076529067631,
        "h2/eaf": 797.2788136434048,
    }
    for test_name, test_inputs in test_cases.items():
        lcoh6_iron_tech.update(test_inputs)
        prob = om.Problem()
        comp = IronComponent(
            plant_config=plant_config,
            tech_config={"model_inputs": {"cost_parameters": lcoh6_iron_tech}},
            driver_config=driver_config,
        )
        prob.model.add_subsystem("iron", comp)
        prob.setup()
        prob.run_model()

        with subtests.test(f"Hibbing mine LCOI for {test_name}"):
            lcoi = prob.get_val("iron.LCOI", units="USD/t")
            assert pytest.approx(lcoi, abs=0.3) == expected_lcoi[test_name]


def test_lcoh3_iron(plant_config, driver_config, lcoh3_iron_tech, subtests):
    test_cases = {
        "ng/none": {"winning_type": "ng", "post_type": "none"},
        "ng/eaf": {"winning_type": "ng", "post_type": "eaf"},
        "h2/none": {"winning_type": "h2", "post_type": "none"},
        "h2/eaf": {"winning_type": "h2", "post_type": "eaf"},
    }

    expected_lcoi = {
        "ng/none": 370.212189551055,
        "ng/eaf": 513.8574754088993,
        "h2/none": 485.58526720893695,
        "h2/eaf": 629.4564279455784,
    }

    for test_name, test_inputs in test_cases.items():
        lcoh3_iron_tech.update(test_inputs)
        prob = om.Problem()
        comp = IronComponent(
            plant_config=plant_config,
            tech_config={"model_inputs": {"cost_parameters": lcoh3_iron_tech}},
            driver_config=driver_config,
        )
        prob.model.add_subsystem("iron", comp)
        prob.setup()
        prob.run_model()

        with subtests.test(f"Hibbing mine LCOI for {test_name}"):
            lcoi = prob.get_val("iron.LCOI", units="USD/t")
            assert pytest.approx(lcoi, abs=0.3) == expected_lcoi[test_name]
