import numpy as np
import pytest
import openmdao.api as om
from pytest import fixture

from h2integrate.core.feedstocks import FeedstockCostModel


plant_life = 30
n_timesteps = 8760
min_cost = 5.0
max_cost = 10.0
avg_cost = (min_cost + max_cost) / 2

min_consumption = 0.1
max_consumption = 0.3
avg_consumption = (min_consumption + max_consumption) / 2


@fixture
def comp_scalar_cost():
    plant_config = {
        "plant_life": 30,
        "simulation": {
            "n_timesteps": 8760,
            "dt": 3600,
        },
    }
    feedstock_cost_input = {
        "water_feedstock": {
            "name": "water",
            "units": "galUS",
            "cost": 7.5,
            "cost_year": 2022,
        }
    }

    tech_config = {"model_inputs": {"cost_parameters": feedstock_cost_input["water_feedstock"]}}

    return plant_config, tech_config


@fixture
def comp_cost_per_year():
    cost_profile = [7.5] * 30

    plant_config = {
        "plant_life": 30,
        "simulation": {
            "n_timesteps": 8760,
            "dt": 3600,
        },
    }
    feedstock_cost_input = {
        "water_feedstock": {
            "name": "water",
            "units": "galUS",
            "cost": cost_profile,
            "cost_year": 2022,
        }
    }

    tech_config = {"model_inputs": {"cost_parameters": feedstock_cost_input["water_feedstock"]}}

    return plant_config, tech_config


@fixture
def comp_cost_per_hour():
    # cost_profile = 5.0*np.ones(8760)
    # cost_profile[0:8760:2] = 10.0
    cost_profile = 7.5 * np.ones(8760)
    plant_config = {
        "plant_life": 30,
        "simulation": {
            "n_timesteps": 8760,
            "dt": 3600,
        },
    }
    feedstock_cost_input = {
        "water_feedstock": {
            "name": "water",
            "units": "galUS",
            "cost": cost_profile.tolist(),
            "cost_year": 2022,
        }
    }

    tech_config = {"model_inputs": {"cost_parameters": feedstock_cost_input["water_feedstock"]}}

    return plant_config, tech_config


def create_prob(comp, input_hourly: bool, input_annual: bool, constant_usage: bool):
    hourly_water_usage = [0.2] * 8760
    annual_water_usage = sum(hourly_water_usage)  # [sum(hourly_water_usage)]*30

    variable_hourly_water_usage = 0.1 * np.ones(8760)
    variable_hourly_water_usage[0:8760:2] = 0.3

    year_even = 0.1 * 8760
    year_odd = 0.3 * 8760

    variable_annual_water_usage = year_even * np.ones(30)
    variable_annual_water_usage[0:30:2] = year_odd

    prob = om.Problem()
    prob.model.add_subsystem("water", comp)
    prob.setup()

    if constant_usage:
        if input_hourly:
            prob.set_val("water.water_consumed", hourly_water_usage, units="galUS")
        if input_annual:
            prob.set_val("water.total_water_consumed", annual_water_usage, units="galUS/yr")
    else:
        if input_hourly:
            prob.set_val("water.water_consumed", variable_hourly_water_usage, units="galUS")
        if input_annual:
            prob.set_val(
                "water.total_water_consumed", variable_annual_water_usage, units="galUS/yr"
            )

    return prob


def test_costs_per_year(comp_cost_per_year, subtests):
    plant_config, tech_config = comp_cost_per_year

    constant_cost_per_year = 7.5 * 0.2 * 8760
    total_varom = constant_cost_per_year * 30
    test_matrix = {
        # should never throw error
        "Both/Constant": [True, True, True],
        "Both/Variable": [True, True, False],
        # should throw error
        "Hourly/Constant": [True, False, True],
        "Hourly/Variable": [True, False, False],
        # should work here
        "Annual/Constant": [False, True, True],
        "Annual/Variable": [False, True, False],
        # should throw error
        "Neither/Constant": [False, False, False],
    }

    for test_name, input_params in test_matrix.items():
        input_desc, profile_desc = test_name.split("/")
        comp = FeedstockCostModel(
            plant_config={"plant": plant_config},
            tech_config=tech_config,
            driver_config={},
            feedstock_name="water_feedstock",
        )
        prob = create_prob(comp, *input_params)

        if input_desc == "Hourly" or input_desc == "Neither":
            if input_desc == "Neither":
                with pytest.raises(ValueError, match="Cost of water provided on annual"):
                    prob.run_model()
            else:
                with pytest.raises(ValueError, match="Cost of water provided on annual"):
                    prob.run_model()
        else:
            prob.run_model()

            varom = prob.get_val("water.VarOpEx")
            if profile_desc == "Constant":
                if input_desc == "Annual" or input_desc == "Both":
                    with subtests.test(
                        f"{input_desc} input(s) provided and {profile_desc} usage: VarOpEx per year"
                    ):
                        assert all(
                            pytest.approx(v, rel=1e-6) == constant_cost_per_year for v in varom
                        )

            if profile_desc == "Variable":
                with subtests.test(
                    f"{input_desc} input(s) provided and {profile_desc} usage: total VarOpEx"
                ):
                    assert pytest.approx(sum(varom), rel=1e-6) == total_varom

                with subtests.test(
                    f"{input_desc} input(s) provided and {profile_desc} usage: VarOpex compare year"
                ):
                    assert varom[0] > varom[1]


def test_costs_per_timestep(comp_cost_per_hour, subtests):
    plant_config, tech_config = comp_cost_per_hour

    constant_cost_per_year = 7.5 * 0.2 * 8760
    total_varom = constant_cost_per_year * 30
    test_matrix = {
        # should never throw error
        "Both/Constant": [True, True, True],
        "Both/Variable": [True, True, False],
        # should work here
        "Hourly/Constant": [True, False, True],
        "Hourly/Variable": [True, False, False],
        # should throw errors
        "Annual/Constant": [False, True, True],
        "Annual/Variable": [False, True, False],
        # should throw error
        "Neither/Constant": [False, False, False],
    }

    for test_name, input_params in test_matrix.items():
        input_desc, profile_desc = test_name.split("/")
        comp = FeedstockCostModel(
            plant_config={"plant": plant_config},
            tech_config=tech_config,
            driver_config={},
            feedstock_name="water_feedstock",
        )
        prob = create_prob(comp, *input_params)

        if input_desc == "Annual" or input_desc == "Neither":
            with pytest.raises(ValueError, match="Cost of water provided per time-step"):
                prob.run_model()

        else:
            prob.run_model()

            varom = prob.get_val("water.VarOpEx")
            if profile_desc == "Constant":
                if input_desc == "Hourly" or input_desc == "Both":
                    with subtests.test(
                        f"{input_desc} input(s) provided and {profile_desc} usage: VarOpEx per year"
                    ):
                        assert all(
                            pytest.approx(v, rel=1e-6) == constant_cost_per_year for v in varom
                        )

            if profile_desc == "Variable":
                with subtests.test(
                    f"{input_desc} input(s) provided and {profile_desc} usage: total VarOpEx"
                ):
                    assert pytest.approx(sum(varom), rel=1e-6) == total_varom

                with subtests.test(
                    f"{input_desc} input(s) provided and {profile_desc} usage: VarOpex per year"
                ):
                    assert all(pytest.approx(v, rel=1e-6) == constant_cost_per_year for v in varom)


def test_flat_cost(comp_scalar_cost, subtests):
    plant_config, tech_config = comp_scalar_cost

    constant_cost_per_year = 7.5 * 0.2 * 8760
    total_varom = constant_cost_per_year * 30
    test_matrix = {
        # should never throw error
        "Both/Constant": [True, True, True],  # never throws error
        "Both/Variable": [True, True, False],  # never throws error
        # should work here
        "Hourly/Constant": [True, False, True],
        "Hourly/Variable": [True, False, False],
        # should work here
        "Annual/Constant": [False, True, True],
        "Annual/Variable": [False, True, False],
        # should give zeros
        "Neither/Constant": [False, False, False],  # results in zero
    }

    for test_name, input_params in test_matrix.items():
        input_desc, profile_desc = test_name.split("/")
        comp = FeedstockCostModel(
            plant_config={"plant": plant_config},
            tech_config=tech_config,
            driver_config={},
            feedstock_name="water_feedstock",
        )
        prob = create_prob(comp, *input_params)

        prob.run_model()

        varom = prob.get_val("water.VarOpEx")
        if profile_desc == "Constant":
            if input_desc == "Neither":
                with subtests.test(
                    f"{input_desc} input(s) provided and {profile_desc} usage: VarOpEx per year"
                ):
                    assert all(pytest.approx(v, rel=1e-6) == 0.0 for v in varom)
            else:
                with subtests.test(
                    f"{input_desc} input(s) provided and {profile_desc} usage: VarOpEx per year"
                ):
                    assert all(pytest.approx(v, rel=1e-6) == constant_cost_per_year for v in varom)

        if profile_desc == "Variable":
            with subtests.test(
                f"{input_desc} input(s) provided and {profile_desc} usage: total VarOpEx"
            ):
                assert pytest.approx(sum(varom), rel=1e-6) == total_varom

            if input_desc == "Hourly":
                with subtests.test(
                    f"{input_desc} input(s) provided and {profile_desc} usage: VarOpex per year"
                ):
                    assert all(pytest.approx(v, abs=0.1) == constant_cost_per_year for v in varom)
            else:
                with subtests.test(
                    f"{input_desc} input(s) provided and {profile_desc} usage: VarOpex compare year"
                ):
                    assert varom[0] > varom[1]
