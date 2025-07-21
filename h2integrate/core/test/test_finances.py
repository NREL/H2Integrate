import openmdao.api as om
from pytest import approx

from h2integrate.core.finances import ProFastComp


def test_electrolyzer_refurb_results():
    plant_config = {
        "finance_parameters": {
            "profast_general_inflation": 0.02,
            "costing_general_inflation": 0.0,
            "sales_tax_rate": 0.07,
            "property_tax": 0.01,
            "property_insurance": 0.005,
            "administrative_expense_percent_of_sales": 0.03,
            "total_income_tax_rate": 0.21,
            "capital_gains_tax_rate": 0.15,
            "discount_rate": 0.08,
            "debt_equity_split": 70,
            "debt_equity_ratio": None,
            "debt_type": "Revolving debt",
            "loan_period": 10,
            "debt_interest_rate": 0.05,
            "cash_onhand_months": 6,
            "depreciation_method": "Straight line",
            "depreciation_period": 20,
            "depreciation_period_electrolyzer": 10,
        },
        "plant": {
            "atb_year": 2022,
            "plant_life": 30,
            "installation_time": 24,
            "cost_year": 2022,
            "grid_connection": True,
            "ppa_price": 0.05,
        },
        "policy_parameters": {
            "electricity_itc": 0.3,
            "h2_storage_itc": 0.3,
            "electricity_ptc": 25,
            "h2_ptc": 3,
        },
    }

    tech_config = {
        "electrolyzer": {
            "model_inputs": {
                "financial_parameters": {
                    "replacement_cost_percent": 0.1,
                }
            }
        },
    }

    prob = om.Problem()
    comp = ProFastComp(plant_config=plant_config, tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])

    prob.setup()

    prob.set_val("capex_adjusted_electrolyzer", 1.0e7, units="USD")
    prob.set_val("opex_adjusted_electrolyzer", 1.0e4, units="USD/year")

    prob.set_val("total_hydrogen_produced", 4.0e5, units="kg/year")
    prob.set_val("time_until_replacement", 5.0e3, units="h")

    prob.run_model()

    assert prob["LCOH"] == approx(4.27529137)


def test_profast_config_provided():
    pf_params = {
        "demand rampup": 0,
        "analysis start year": 2024,
        "operating life": 30,
        "installation months": 24,
        "TOPC": {"unit price": 0.0, "decay": 0.0, "support utilization": 0.0, "sunset years": 0},
        "commodity": {"name": "Hydrogen", "unit": "kg", "initial price": 100, "escalation": 0.02},
        "annual operating incentive": {
            "value": 0.0,
            "decay": 0.0,
            "sunset years": 0,
            "taxable": True,
        },
        "incidental revenue": {"value": 0.0, "escalation": 0.0},
        "credit card fees": 0,
        "sales tax": 0.07,
        "road tax": {"value": 0.0, "escalation": 0.0},
        "labor": {"value": 0.0, "rate": 0.0, "escalation": 0.0},
        "maintenance": {"value": 0, "escalation": 0.02},
        "rent": {"value": 0, "escalation": 0.02},
        "license and permit": {"value": 0, "escalation": 0.02},
        "non depr assets": 0.0,
        "end of proj sale non depr assets": 0.0,
        "installation cost": {
            "value": 0,
            "depr type": "Straight line",
            "depr period": 4,
            "depreciable": False,
        },
        "one time cap inct": {
            "value": 0.0,
            "depr type": "MACRS",
            "depr period": 3,
            "depreciable": True,
        },
        "property tax and insurance": 0.015,
        "admin expense": 0.03,
        "tax loss carry forward years": 0,
        "capital gains tax rate": 0.15,
        "tax losses monetized": True,
        "sell undepreciated cap": True,
        "loan period if used": 10,
        "debt equity ratio of initial financing": 2.3333333333333335,
        "debt interest rate": 0.05,
        "debt type": "Revolving debt",
        "total income tax rate": 0.21,
        "cash onhand": 6,
        "general inflation rate": 0.02,
        "leverage after tax nominal discount rate": 0.08,
    }
    plant_config = {
        "finance_parameters": {
            "profast_general_inflation": 0.02,
            "costing_general_inflation": 0.0,
            "pf_params": {"params": pf_params},
            "depreciation_method": "Straight line",
            "depreciation_period": 20,
            "depreciation_period_electrolyzer": 10,
        },
        "plant": {
            "atb_year": 2022,
            "plant_life": 30,
            "installation_time": 24,
            "cost_year": 2022,
            "grid_connection": True,
            "ppa_price": 0.05,
        },
        "policy_parameters": {
            "electricity_itc": 0.3,
            "h2_storage_itc": 0.3,
            "electricity_ptc": 25,
            "h2_ptc": 3,
        },
    }

    tech_config = {
        "electrolyzer": {
            "model_inputs": {
                "financial_parameters": {
                    "replacement_cost_percent": 0.1,
                }
            }
        },
    }

    prob = om.Problem()
    comp = ProFastComp(plant_config=plant_config, tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])

    prob.setup()

    prob.set_val("capex_adjusted_electrolyzer", 1.0e7, units="USD")
    prob.set_val("opex_adjusted_electrolyzer", 1.0e4, units="USD/year")

    prob.set_val("total_hydrogen_produced", 4.0e5, units="kg/year")
    prob.set_val("time_until_replacement", 5.0e3, units="h")

    prob.run_model()

    assert prob["LCOH"] == approx(4.27529137)
