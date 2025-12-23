import numpy as np
import pytest
import openmdao.api as om
from pytest import fixture

from h2integrate import EXAMPLE_DIR
from h2integrate.core.inputs.validation import load_driver_yaml
from h2integrate.converters.iron.ng_iron_dri_cost_model import (
    NaturalGasIronReductionPlantCostComponent,
)
from h2integrate.converters.iron.ng_iron_dri_perf_model import (
    NaturalGasIronReductionPlantPerformanceComponent,
)


@fixture
def plant_config():
    plant_config = {
        "plant": {
            "plant_life": 30,
            "simulation": {
                "n_timesteps": 8760,
                "dt": 3600,
            },
        },
        "finance_parameters": {
            "cost_adjustment_parameters": {
                "cost_year_adjustment_inflation": 0.025,
                "target_dollar_year": 2022,
            }
        },
    }
    return plant_config


@fixture
def driver_config():
    driver_config = load_driver_yaml(EXAMPLE_DIR / "21_iron_mn_to_il" / "driver_config.yaml")
    return driver_config


@fixture
def ng_dri_base_config():
    tech_config = {
        "model_inputs": {
            "shared_parameters": {
                "pig_iron_production_rate_tonnes_per_hr": 1418095 / 8760,  # t/h
            },
            "cost_parameters": {
                "skilled_labor_cost": 40.85,  # 2022 USD/hr
                "unskilled_labor_cost": 30.0,  # 2022 USD/hr
            },
        }
    }
    return tech_config


@fixture
def feedstock_availability_costs():
    feedstocks_dict = {
        "electricity": {
            "rated_capacity": 27000,  # need 26949.46472431 kW
            "units": "kW",
            "price": 0.05802,  # USD/kW
        },
        "natural_gas": {
            "rated_capacity": 1270,  # need 1268.934 MMBtu at each timestep
            "units": "MMBtu",
            "price": 0.0,
        },
        "reformer_catalyst": {
            "rated_capacity": 0.001,  # need 0.00056546 m**3/h
            "units": "m**3",
            "price": 0.0,
        },
        "water": {
            "rated_capacity": 40.0,  # need 38.71049649 galUS/h
            "units": "galUS",
            "price": 1670.0,  # cost is $0.441167535/t, equal to $1670.0004398318847/galUS
        },
        "iron_ore": {
            "rated_capacity": 263.75,
            "units": "t/h",
            "price": 27.5409 * 1e3,  # USD/t
        },
    }
    return feedstocks_dict


def test_ng_dri_performance(
    plant_config, ng_dri_base_config, feedstock_availability_costs, subtests
):
    expected_pig_iron_annual_production_tpd = 3885.1917808219177  # t/d

    prob = om.Problem()

    iron_dri_perf = NaturalGasIronReductionPlantPerformanceComponent(
        plant_config=plant_config,
        tech_config=ng_dri_base_config,
        driver_config={},
    )
    prob.model.add_subsystem("perf", iron_dri_perf, promotes=["*"])
    prob.setup()

    for feedstock_name, feedstock_info in feedstock_availability_costs.items():
        prob.set_val(
            f"perf.{feedstock_name}_in",
            feedstock_info["rated_capacity"],
            units=feedstock_info["units"],
        )
    prob.run_model()

    annual_pig_iron = np.sum(prob.get_val("perf.pig_iron_out", units="t/h"))
    with subtests.test("Annual Pig Iron"):
        assert (
            pytest.approx(annual_pig_iron / 365, rel=1e-3)
            == expected_pig_iron_annual_production_tpd
        )


def test_ng_dri_performance_cost(
    plant_config, ng_dri_base_config, feedstock_availability_costs, subtests
):
    expected_capex = 403808062.6981323
    expected_fixed_om = 60103761.59958463
    expected_pig_iron_annual_production_tpd = 3885.1917808219177  # t/d

    prob = om.Problem()

    iron_dri_perf = NaturalGasIronReductionPlantPerformanceComponent(
        plant_config=plant_config,
        tech_config=ng_dri_base_config,
        driver_config={},
    )
    iron_dri_cost = NaturalGasIronReductionPlantCostComponent(
        plant_config=plant_config,
        tech_config=ng_dri_base_config,
        driver_config={},
    )

    prob.model.add_subsystem("perf", iron_dri_perf, promotes=["*"])
    prob.model.add_subsystem("cost", iron_dri_cost, promotes=["*"])
    prob.setup()

    for feedstock_name, feedstock_info in feedstock_availability_costs.items():
        prob.set_val(
            f"perf.{feedstock_name}_in",
            feedstock_info["rated_capacity"],
            units=feedstock_info["units"],
        )

    prob.run_model()

    # difference from IronPlantCostComponent:
    # IronPlantCostComponent: maintenance_materials is included in Fixed OpEx
    # NaturalGasIronReductionPlantCostComponent: maintenance_materials is the variable O&M

    annual_pig_iron = np.sum(prob.get_val("perf.pig_iron_out", units="t/h"))
    with subtests.test("Annual Pig Iron"):
        assert (
            pytest.approx(annual_pig_iron / 365, rel=1e-3)
            == expected_pig_iron_annual_production_tpd
        )
    with subtests.test("CapEx"):
        # expected difference of 0.044534%
        assert pytest.approx(prob.get_val("cost.CapEx")[0], rel=1e-3) == expected_capex
    with subtests.test("OpEx"):
        assert (
            pytest.approx(prob.get_val("cost.OpEx")[0] + prob.get_val("cost.VarOpEx")[0], rel=1e-3)
            == expected_fixed_om
        )
