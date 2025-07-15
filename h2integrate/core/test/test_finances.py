import unittest
from pathlib import Path

import pytest
import openmdao.api as om

from h2integrate.core.finances import ProFastComp
from h2integrate.core.inputs.validation import load_tech_yaml, load_plant_yaml


examples_dir = Path(__file__).resolve().parent.parent.parent.parent / "examples/."


class TestProFastComp(unittest.TestCase):
    def setUp(self):
        self.plant_config = {
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

        self.tech_config = {
            "electrolyzer": {
                "model_inputs": {
                    "financial_parameters": {
                        "replacement_cost_percent": 0.1,
                    }
                }
            },
        }

    def test_electrolyzer_refurb_results(self):
        prob = om.Problem()
        comp = ProFastComp(
            plant_config=self.plant_config, tech_config=self.tech_config, commodity_type="hydrogen"
        )
        prob.model.add_subsystem("comp", comp, promotes=["*"])

        prob.setup()

        prob.set_val("capex_adjusted_electrolyzer", 1.0e7, units="USD")
        prob.set_val("opex_adjusted_electrolyzer", 1.0e4, units="USD/year")

        prob.set_val("total_hydrogen_produced", 4.0e5, units="kg/year")
        prob.set_val("time_until_replacement", 5.0e3, units="h")

        prob.run_model()

        self.assertAlmostEqual(prob["LCOH"][0], 4.27529137, places=7)

    def test_modified_lcoe_calc(self):
        # Set up paths
        example_case_dir = examples_dir / "01_onshore_steel_mn"

        tech_config = load_tech_yaml(example_case_dir / "tech_config.yaml")
        plant_config = load_plant_yaml(example_case_dir / "plant_config.yaml")

        # Run ProFastComp with loaded configs
        prob = om.Problem()
        comp = ProFastComp(
            plant_config=plant_config,
            tech_config=tech_config["technologies"],
            commodity_type="electricity",
        )
        prob.model.add_subsystem("comp", comp, promotes=["*"])

        prob.setup()

        prob.set_val("capex_adjusted_hopp", 2.0e7, units="USD")
        prob.set_val("opex_adjusted_hopp", 2.0e4, units="USD/year")
        prob.set_val("capex_adjusted_electrolyzer", 1.0e7, units="USD")
        prob.set_val("opex_adjusted_electrolyzer", 1.0e4, units="USD/year")
        prob.set_val("capex_adjusted_h2_storage", 5.0e6, units="USD")
        prob.set_val("opex_adjusted_h2_storage", 5.0e3, units="USD/year")
        prob.set_val("capex_adjusted_steel", 3.0e6, units="USD")
        prob.set_val("opex_adjusted_steel", 3.0e3, units="USD/year")
        prob.set_val("total_electricity_produced", 2.0e7, units="kW*h/year")

        prob.run_model()

        self.assertAlmostEqual(prob["LCOE"][0], 0.10616471876960568, places=7)

    def test_lcoe_with_selected_technologies(self):
        # Set up paths
        example_case_dir = examples_dir / "01_onshore_steel_mn"

        tech_config = load_tech_yaml(example_case_dir / "tech_config.yaml")
        plant_config = load_plant_yaml(example_case_dir / "plant_config.yaml")

        # Only include HOPP and electrolyzer in metrics
        plant_config["finance_parameters"]["technologies_included_in_metrics"]["LCOE"] = [
            "hopp",
            "steel",
        ]

        prob = om.Problem()
        comp = ProFastComp(
            plant_config=plant_config,
            tech_config=tech_config["technologies"],
            commodity_type="electricity",
        )
        prob.model.add_subsystem("comp", comp, promotes=["*"])

        prob.setup()

        prob.set_val("capex_adjusted_hopp", 2.0e7, units="USD")
        prob.set_val("opex_adjusted_hopp", 2.0e4, units="USD/year")
        prob.set_val("capex_adjusted_electrolyzer", 1.0e7, units="USD")
        prob.set_val("opex_adjusted_electrolyzer", 1.0e4, units="USD/year")
        prob.set_val("capex_adjusted_h2_storage", 5.0e6, units="USD")
        prob.set_val("opex_adjusted_h2_storage", 5.0e3, units="USD/year")
        prob.set_val("capex_adjusted_steel", 3.0e6, units="USD")
        prob.set_val("opex_adjusted_steel", 3.0e3, units="USD/year")
        prob.set_val("total_electricity_produced", 2.0e7, units="kW*h/year")

        prob.run_model()

        self.assertAlmostEqual(prob["LCOE"][0], 0.12208942658504653, places=6)

    def test_lcoe_with_invalid_technology(self):
        # Set up paths
        example_case_dir = examples_dir / "01_onshore_steel_mn"

        tech_config = load_tech_yaml(example_case_dir / "tech_config.yaml")
        plant_config = load_plant_yaml(example_case_dir / "plant_config.yaml")

        # Add an invalid technology
        plant_config["finance_parameters"]["technologies_included_in_metrics"]["LCOE"] = [
            "hopp",
            "dummy_tech",
        ]

        prob = om.Problem()
        comp = ProFastComp(
            plant_config=plant_config,
            tech_config=tech_config["technologies"],
            commodity_type="electricity",
        )
        prob.model.add_subsystem("comp", comp, promotes=["*"])

        error_msg = "not found in tech_config"
        with pytest.raises(ValueError, match=error_msg):
            prob.setup()
