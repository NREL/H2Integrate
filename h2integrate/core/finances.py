import numpy as np
import ProFAST  # system financial model
import openmdao.api as om
import numpy_financial as npf


class AdjustedCapexOpexComp(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("tech_config", types=dict)
        self.options.declare("plant_config", types=dict)

    def setup(self):
        tech_config = self.options["tech_config"]
        plant_config = self.options["plant_config"]
        self.discount_years = plant_config["finance_parameters"]["discount_years"]
        self.inflation_rate = plant_config["finance_parameters"]["costing_general_inflation"]
        self.cost_year = plant_config["plant"]["cost_year"]

        for tech in tech_config:
            self.add_input(f"capex_{tech}", val=0.0, units="USD")
            self.add_input(f"opex_{tech}", val=0.0, units="USD/year")
            self.add_output(f"capex_adjusted_{tech}", val=0.0, units="USD")
            self.add_output(f"opex_adjusted_{tech}", val=0.0, units="USD/year")

        self.add_output("total_capex_adjusted", val=0.0, units="USD")
        self.add_output("total_opex_adjusted", val=0.0, units="USD/year")

    def compute(self, inputs, outputs):
        total_capex_adjusted = 0.0
        total_opex_adjusted = 0.0
        for tech in self.options["tech_config"]:
            capex = float(inputs[f"capex_{tech}"][0])
            opex = float(inputs[f"opex_{tech}"][0])
            cost_year = self.discount_years[tech]
            periods = self.cost_year - cost_year
            adjusted_capex = -npf.fv(self.inflation_rate, periods, 0.0, capex)
            adjusted_opex = -npf.fv(self.inflation_rate, periods, 0.0, opex)
            outputs[f"capex_adjusted_{tech}"] = adjusted_capex
            outputs[f"opex_adjusted_{tech}"] = adjusted_opex
            total_capex_adjusted += adjusted_capex
            total_opex_adjusted += adjusted_opex

        outputs["total_capex_adjusted"] = total_capex_adjusted
        outputs["total_opex_adjusted"] = total_opex_adjusted


class ProFastComp(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("tech_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("commodity_type", types=str)

    def setup(self):
        tech_config = self.tech_config = self.options["tech_config"]
        plant_config = self.plant_config = self.options["plant_config"]
        self.discount_rate = plant_config["finance_parameters"]["discount_rate"]
        self.inflation_rate = plant_config["finance_parameters"]["costing_general_inflation"]
        self.cost_year = plant_config["plant"]["cost_year"]

        # Check if the user defined specific technologies to include in the metrics.
        # If provided, only include those technologies in the stackup.
        # If not provided, include all technologies in the financial group in the stackup.
        metrics_map = {
            "hydrogen": "LCOH",
            "electricity": "LCOE",
            "ammonia": "LCOA",
        }
        metric_key = metrics_map.get(self.options["commodity_type"])
        self.included_techs = (
            plant_config["finance_parameters"]
            .get("technologies_included_in_metrics", {})
            .get(metric_key, None)
        )

        # Check if the included technologies are valid
        if self.included_techs is not None:
            missing_techs = [tech for tech in self.included_techs if tech not in tech_config]
            if missing_techs:
                raise ValueError(
                    f"Included technology(ies) {missing_techs} not found in tech_config. "
                    f"Available techs: {list(tech_config.keys())}"
                )

        # If no specific technologies are included, default to all technologies in tech_config
        if self.included_techs is None:
            self.included_techs = list(tech_config.keys())

        for tech in tech_config:
            self.add_input(f"capex_adjusted_{tech}", val=0.0, units="USD")
            self.add_input(f"opex_adjusted_{tech}", val=0.0, units="USD/year")

        if self.options["commodity_type"] == "hydrogen":
            self.add_input("total_hydrogen_produced", val=0.0, units="kg/year")
            self.add_output("LCOH", val=0.0, units="USD/kg")

        if self.options["commodity_type"] == "electricity":
            self.add_input("total_electricity_produced", val=0.0, units="kW*h/year")
            self.add_output("LCOE", val=0.0, units="USD/kW/h")

        if self.options["commodity_type"] == "ammonia":
            self.add_input("total_ammonia_produced", val=0.0, units="kg/year")
            self.add_output("LCOA", val=0.0, units="USD/kg")

        if "electrolyzer" in tech_config:
            self.add_input("time_until_replacement", units="h")

    def compute(self, inputs, outputs):
        finance_parameters = self.plant_config["finance_parameters"]
        gen_inflation = finance_parameters["profast_general_inflation"]
        commodity_type = self.options["commodity_type"]

        land_cost = 0.0

        pf = ProFAST.ProFAST()
        if commodity_type == "hydrogen":
            pf.set_params(
                "commodity",
                {
                    "name": "Hydrogen",
                    "unit": "kg",
                    "initial price": 100,
                    "escalation": gen_inflation,
                },
            )
            pf.set_params(
                "capacity",
                float(inputs["total_hydrogen_produced"]) / 365.0,
            )  # kg/day
        elif commodity_type == "ammonia":
            pf.set_params(
                "commodity",
                {
                    "name": "Ammonia",
                    "unit": "kg",
                    "initial price": 100,
                    "escalation": gen_inflation,
                },
            )
            pf.set_params(
                "capacity",
                float(inputs["total_ammonia_produced"]) / 365.0,
            )
        elif commodity_type == "electricity":
            pf.set_params(
                "commodity",
                {
                    "name": "Electricity",
                    "unit": "kWh",
                    "initial price": 100,
                    "escalation": gen_inflation,
                },
            )
            pf.set_params(
                "capacity",
                float(inputs["total_electricity_produced"]) / 365.0,
            )

        pf.set_params("maintenance", {"value": 0, "escalation": gen_inflation})
        pf.set_params(
            "analysis start year",
            self.plant_config["plant"]["atb_year"] + 2,  # Add financial analysis start year
        )
        pf.set_params("operating life", self.plant_config["plant"]["plant_life"])
        pf.set_params(
            "installation months",
            self.plant_config["plant"][
                "installation_time"
            ],  # Add installation time to yaml default=0
        )
        pf.set_params(
            "installation cost",
            {
                "value": 0,
                "depr type": "Straight line",
                "depr period": 4,
                "depreciable": False,
            },
        )
        if land_cost > 0:
            pf.set_params("non depr assets", land_cost)
            pf.set_params(
                "end of proj sale non depr assets",
                land_cost * (1 + gen_inflation) ** self.plant_config["plant"]["plant_life"],
            )
        pf.set_params("demand rampup", 0)
        pf.set_params("long term utilization", 1)  # TODO should use utilization
        pf.set_params("credit card fees", 0)
        pf.set_params("sales tax", finance_parameters["sales_tax_rate"])
        pf.set_params("license and permit", {"value": 00, "escalation": gen_inflation})
        pf.set_params("rent", {"value": 0, "escalation": gen_inflation})
        # TODO how to handle property tax and insurance for fully offshore?
        pf.set_params(
            "property tax and insurance",
            finance_parameters["property_tax"] + finance_parameters["property_insurance"],
        )
        pf.set_params(
            "admin expense",
            finance_parameters["administrative_expense_percent_of_sales"],
        )
        pf.set_params(
            "total income tax rate",
            finance_parameters["total_income_tax_rate"],
        )
        pf.set_params(
            "capital gains tax rate",
            finance_parameters["capital_gains_tax_rate"],
        )
        pf.set_params("sell undepreciated cap", True)
        pf.set_params("tax losses monetized", True)
        pf.set_params("general inflation rate", gen_inflation)
        pf.set_params(
            "leverage after tax nominal discount rate",
            finance_parameters["discount_rate"],
        )
        if finance_parameters["debt_equity_split"]:
            pf.set_params(
                "debt equity ratio of initial financing",
                (
                    finance_parameters["debt_equity_split"]
                    / (100 - finance_parameters["debt_equity_split"])
                ),
            )  # TODO this may not be put in right
        elif finance_parameters["debt_equity_ratio"]:
            pf.set_params(
                "debt equity ratio of initial financing",
                (finance_parameters["debt_equity_ratio"]),
            )  # TODO this may not be put in right
        pf.set_params("debt type", finance_parameters["debt_type"])
        pf.set_params("loan period if used", finance_parameters["loan_period"])
        pf.set_params(
            "debt interest rate",
            finance_parameters["debt_interest_rate"],
        )
        pf.set_params("cash onhand", finance_parameters["cash_onhand_months"])

        # --------------------------------- Add capital and fixed items to ProFAST --------------
        for tech in self.tech_config:
            # Only add if tech is included in the user's desired stackup for that metric
            if tech not in self.included_techs:
                continue
            if "electrolyzer" in tech:
                electrolyzer_refurbishment_schedule = np.zeros(
                    self.plant_config["plant"]["plant_life"]
                )
                refurb_period = round(float(inputs["time_until_replacement"]) / (24 * 365))
                electrolyzer_refurbishment_schedule[
                    refurb_period : self.plant_config["plant"]["plant_life"] : refurb_period
                ] = self.tech_config["electrolyzer"]["model_inputs"]["financial_parameters"][
                    "replacement_cost_percent"
                ]
                electrolyzer_refurbishment_schedule = list(electrolyzer_refurbishment_schedule)

                pf.add_capital_item(
                    name="Electrolysis System",
                    cost=float(inputs[f"capex_adjusted_{tech}"]),
                    depr_type=finance_parameters["depreciation_method"],
                    depr_period=int(finance_parameters["depreciation_period_electrolyzer"]),
                    refurb=electrolyzer_refurbishment_schedule,
                )
                pf.add_fixed_cost(
                    name="Electrolysis System Fixed O&M Cost",
                    usage=1.0,
                    unit="$/year",
                    cost=float(inputs[f"opex_adjusted_{tech}"]),
                    escalation=gen_inflation,
                )
            else:
                pf.add_capital_item(
                    name=f"{tech} System",
                    cost=float(inputs[f"capex_adjusted_{tech}"]),
                    depr_type=finance_parameters["depreciation_method"],
                    depr_period=finance_parameters["depreciation_period"],
                    refurb=[0],
                )
                pf.add_fixed_cost(
                    name=f"{tech} O&M Cost",
                    usage=1.0,
                    unit="$/year",
                    cost=float(inputs[f"opex_adjusted_{tech}"]),
                    escalation=gen_inflation,
                )

        # ------------------------------------ solve and post-process -----------------------------

        sol = pf.solve_price()

        # Only hydrogen supported in the very short term
        if self.options["commodity_type"] == "hydrogen":
            outputs["LCOH"] = sol["price"]

        elif self.options["commodity_type"] == "ammonia":
            outputs["LCOA"] = sol["price"]

        elif self.options["commodity_type"] == "electricity":
            outputs["LCOE"] = sol["price"]
