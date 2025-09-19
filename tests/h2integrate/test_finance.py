import os
from pathlib import Path

import pytest
from pytest import approx

from h2integrate import EXAMPLE_DIR
from h2integrate.core.dict_utils import update_defaults
from h2integrate.tools.profast_tools import (
    run_profast,
    create_years_of_operation,
    create_and_populate_profast,
)
from h2integrate.core.h2integrate_model import H2IntegrateModel
from h2integrate.core.inputs.validation import load_yaml


def test_calc_financial_parameter_weighted_average_by_capex(subtests):
    from h2integrate.tools.eco.finance import calc_financial_parameter_weighted_average_by_capex

    with subtests.test("single value"):
        h2integrate_config = {"finance_parameters": {"discount_rate": 0.1}}

        assert (
            calc_financial_parameter_weighted_average_by_capex(
                "discount_rate", h2integrate_config=h2integrate_config, capex_breakdown={}
            )
            == 0.1
        )

    with subtests.test("weighted average value - all values specified"):
        h2integrate_config = {"finance_parameters": {"discount_rate": {"wind": 0.05, "solar": 0.1}}}

        capex_breakdown = {"wind": 1e9, "solar": 1e8}

        return_value = calc_financial_parameter_weighted_average_by_capex(
            "discount_rate", h2integrate_config=h2integrate_config, capex_breakdown=capex_breakdown
        )

        assert return_value == approx(0.05454545454545454)

    with subtests.test("weighted average value - not all values specified"):
        h2integrate_config = {
            "finance_parameters": {"discount_rate": {"wind": 0.05, "solar": 0.1, "general": 0.15}}
        }

        capex_breakdown = {"wind": 1e9, "solar": 1e8, "electrolyzer": 3e8, "battery": 2e8}

        return_value = calc_financial_parameter_weighted_average_by_capex(
            "discount_rate", h2integrate_config=h2integrate_config, capex_breakdown=capex_breakdown
        )

        assert return_value == approx(0.084375)


def test_variable_om_no_escalation(subtests):
    os.chdir(EXAMPLE_DIR / "02_texas_ammonia")

    inflation_rate = 0.0
    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "02_texas_ammonia.yaml")

    # Run the model
    model.run()

    model.post_process()

    with subtests.test("Check original LCOH with zero escalation"):
        assert (
            pytest.approx(model.prob.get_val("finance_subgroup_hydrogen.LCOH")[0], rel=1e-3)
            == 3.9705799099
        )

    outputs_dir = Path.cwd() / "outputs"

    yaml_fpath = outputs_dir / "profast_output_hydrogen_config.yaml"

    pf_dict = load_yaml(yaml_fpath)

    plant_life = int(pf_dict["params"]["operating life"])

    years_of_operation = create_years_of_operation(
        plant_life,
        pf_dict["params"]["analysis start year"],
        pf_dict["params"]["installation months"],
    )

    pf_dict = update_defaults(pf_dict, "escalation", inflation_rate)
    pf_dict["params"].update({"general inflation rate": inflation_rate})

    water_cost_per_gal = 0.003  # [$/gal]
    gal_water_pr_kg_H2 = 3.8  # [gal H2O / kg-H2]

    # calculate annual water cost
    annual_h2_kg = pf_dict["params"]["capacity"] * pf_dict["params"]["long term utilization"] * 365
    annual_water_gal = annual_h2_kg * gal_water_pr_kg_H2
    annual_water_cost_USD_per_kg = annual_water_gal * water_cost_per_gal / annual_h2_kg
    water_feedstock_entry = {
        "Water": {
            "escalation": inflation_rate,
            "unit": "$/kg",
            "usage": 1.0,
            "cost": annual_water_cost_USD_per_kg,
        }
    }

    # update feedstock entry
    pf_dict["feedstocks"].update(water_feedstock_entry)

    # run profast for feedstock cost as a scalar
    pf = create_and_populate_profast(pf_dict)
    sol_scalar, summary_scalar, price_breakdown_scalar = run_profast(pf)

    with subtests.test(
        "Check variable o&m as scalar LCOH against original LCOH with zero escalation"
    ):
        assert sol_scalar["price"] > model.prob.get_val("finance_subgroup_hydrogen.LCOH")[0]

    with subtests.test("Check variable o&m as scalar LCOH with zero escalation value"):
        assert pytest.approx(sol_scalar["price"], rel=1e-3) == 3.98205152215

    # create water cost entry as array
    annual_water_cost_USD_per_year = [annual_water_cost_USD_per_kg] * plant_life
    annual_water_cost_USD_per_year_dict = dict(
        zip(years_of_operation, annual_water_cost_USD_per_year)
    )
    water_feedstock_entry = {
        "Water": {
            "escalation": inflation_rate,
            "unit": "$/kg",
            "usage": 1.0,
            "cost": annual_water_cost_USD_per_year_dict,
        }
    }

    # update feedstock entry
    pf_dict["feedstocks"].update(water_feedstock_entry)

    pf = create_and_populate_profast(pf_dict)
    sol_list, summary_list, price_breakdown_list = run_profast(pf)
    with subtests.test(
        "Check variable o&m as array LCOH against original LCOH with zero escalation"
    ):
        assert sol_list["price"] > model.prob.get_val("finance_subgroup_hydrogen.LCOH")[0]

    with subtests.test("Check variable o&m as array LCOH with zero escalation value"):
        assert pytest.approx(sol_list["price"], rel=1e-3) == 3.98205152215

    with subtests.test(
        "Check variable o&m as scalar and as array have same LCOH with zero escalation"
    ):
        assert pytest.approx(sol_list["price"], rel=1e-6) == sol_scalar["price"]


def test_variable_om_with_escalation(subtests):
    os.chdir(EXAMPLE_DIR / "02_texas_ammonia")

    inflation_rate = 0.025
    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "02_texas_ammonia.yaml")

    # Run the model
    model.run()

    outputs_dir = Path.cwd() / "outputs"

    yaml_fpath = outputs_dir / "profast_output_hydrogen_config.yaml"

    # load the profast dictionary
    pf_dict = load_yaml(yaml_fpath)

    plant_life = int(pf_dict["params"]["operating life"])

    years_of_operation = create_years_of_operation(
        plant_life,
        pf_dict["params"]["analysis start year"],
        pf_dict["params"]["installation months"],
    )

    # update the inflation rate
    pf_dict = update_defaults(pf_dict, "escalation", inflation_rate)
    pf_dict["params"].update({"general inflation rate": inflation_rate})

    # rerun profast without variable o&m costs
    pf = create_and_populate_profast(pf_dict)
    sol_init, summary_init, price_breakdown_init = run_profast(pf)

    with subtests.test("Check original LCOH with escalation"):
        assert pytest.approx(sol_init["price"], rel=1e-3) == 2.9981730

    # calculate annual water cost
    water_cost_per_gal = 0.003  # [$/gal]
    gal_water_pr_kg_H2 = 3.8  # [gal H2O / kg-H2]
    annual_h2_kg = pf_dict["params"]["capacity"] * pf_dict["params"]["long term utilization"] * 365
    annual_water_gal = annual_h2_kg * gal_water_pr_kg_H2

    # calculate water cost per kg H2
    annual_water_cost_USD_per_kg = annual_water_gal * water_cost_per_gal / annual_h2_kg
    water_feedstock_entry = {
        "Water": {
            "escalation": inflation_rate,
            "unit": "$/kg",
            "usage": 1.0,
            "cost": annual_water_cost_USD_per_kg,
        }
    }

    # update feedstock entry
    pf_dict["feedstocks"].update(water_feedstock_entry)

    # run profast for feedstock cost as a scalar
    pf = create_and_populate_profast(pf_dict)
    sol_scalar, summary_scalar, price_breakdown_scalar = run_profast(pf)

    with subtests.test("Check variable o&m as scalar LCOH against original LCOH with escalation"):
        assert sol_scalar["price"] > sol_init["price"]

    with subtests.test("Check variable o&m as scalar LCOH with escalation value"):
        assert pytest.approx(sol_scalar["price"], rel=1e-3) == 3.00964412171

    # calculate water cost per kg-H2 and format for costs per year
    annual_water_cost_USD_per_year = [annual_water_cost_USD_per_kg] * plant_life
    annual_water_cost_USD_per_year_dict = dict(
        zip(years_of_operation, annual_water_cost_USD_per_year)
    )
    water_feedstock_entry = {
        "Water": {
            "escalation": inflation_rate,
            "unit": "$/kg",
            "usage": 1.0,
            "cost": annual_water_cost_USD_per_year_dict,
        }
    }

    # update feedstock entry
    pf_dict["feedstocks"].update(water_feedstock_entry)

    # run profast for feedstock cost as an array
    pf = create_and_populate_profast(pf_dict)
    sol_list, summary_list, price_breakdown_list = run_profast(pf)
    with subtests.test("Check variable o&m as array LCOH against original LCOH with escalation"):
        assert sol_list["price"] > sol_init["price"]

    with subtests.test("Check variable o&m as array LCOH with escalation value"):
        assert pytest.approx(sol_list["price"], rel=1e-3) == 3.0062575558

    with subtests.test("Check variable o&m as array LCOH is less than variable o&m as scalar LCOH"):
        assert sol_scalar["price"] > sol_list["price"]
