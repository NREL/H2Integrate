import numpy as np
import ProFAST  # system financial model
import openmdao.api as om
import numpy_financial as npf

from h2integrate.core.utilities import check_plant_config_and_profast_params


class AdjustedCapexOpexComp(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
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
    """
    This component calculates the Levelized Cost of Commodity (LCO) for a user-defined set
    of technologies and commodities, including hydrogen (LCOH), electricity (LCOE),
    ammonia (LCOA), and CO2 (LCOC). Only the user-defined technologies specified in the
    `tech_config` are included in the LCO stackup (or all if no specific technologies are defined).

    Attributes:
        tech_config (dict): Dictionary specifying the technologies to include in the
            LCO calculation. Only these technologies are considered in the stackup.
        plant_config (dict): Plant configuration parameters, including financial and
            operational settings.
        driver_config (dict): Driver configuration parameters (not directly used in calculations).
        commodity_type (str): The type of commodity for which the LCO is calculated.
            Supported values are "hydrogen", "electricity", "ammonia", and "co2".

    Inputs:
        capex_adjusted_{tech} (float): Adjusted capital expenditure for each
            user-defined technology, in USD.
        opex_adjusted_{tech} (float): Adjusted operational expenditure for each
            user-defined technology, in USD/year.
        total_{commodity}_produced (float): Total annual production of the selected commodity
            (units depend on commodity type).
        time_until_replacement (float): Time until electrolyzer replacement, in hours
            (only if "electrolyzer" is in tech_config).
        co2_capture_kgpy (float): Total annual CO2 captured, in kg/year
            (only for commodity_type "co2").

    Outputs:
        LCOH (float): Levelized Cost of Hydrogen, in USD/kg (if commodity_type is "hydrogen").
        LCOE (float): Levelized Cost of Electricity, in USD/kWh
            (if commodity_type is "electricity").
        LCOA (float): Levelized Cost of Ammonia, in USD/kg (if commodity_type is "ammonia").
        LCOC (float): Levelized Cost of CO2, in USD/kg (if commodity_type is "co2").

    Methods:
        initialize(): Declares component options.
        setup(): Defines inputs and outputs based on user configuration and validates
            required parameters.
        compute(inputs, outputs): Assembles financial parameters, adds capital and fixed cost
            items for user-defined technologies, runs the ProFAST financial model,
            and sets the appropriate LCO output.

    Notes:
        - Only technologies specified by the user in `tech_config` are included in the LCO stackup.
        - The component supports flexible configuration for different commodities
            and technology mixes.
        - Financial and operational parameters are primarily sourced from `plant_config`.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("tech_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("commodity_type", types=str)

    def setup(self):
        tech_config = self.tech_config = self.options["tech_config"]
        self.plant_config = self.options["plant_config"]

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

        if self.options["commodity_type"] == "nitrogen":
            self.add_input("total_nitrogen_produced", val=0.0, units="kg/year")
            self.add_output("LCON", val=0.0, units="USD/kg")

        if self.options["commodity_type"] == "co2":
            self.add_input("co2_capture_kgpy", val=0.0, units="kg/year")
            self.add_output("LCOC", val=0.0, units="USD/kg")

        if "electrolyzer" in tech_config:
            self.add_input("time_until_replacement", units="h")

        # Parameter validation checks
        params = {}
        if "pf_params" in self.plant_config["finance_parameters"]:
            pf_params = self.plant_config["finance_parameters"]["pf_params"]["params"]
            params.update(pf_params)

        check_plant_config_and_profast_params(
            self.plant_config["plant"], params, "installation_time", "installation months"
        )
        check_plant_config_and_profast_params(
            self.plant_config["plant"], params, "plant_life", "operating life"
        )
        check_plant_config_and_profast_params(
            self.plant_config["plant"],
            params,
            "financial_analysis_start_year",
            "analysis start year",
        )

    def compute(self, inputs, outputs):
        mass_commodities = ["hydrogen", "ammonia", "co2", "nitrogen"]

        if "pf_params" in self.plant_config["finance_parameters"]:
            gen_inflation = self.plant_config["finance_parameters"]["pf_params"]["params"][
                "general inflation rate"
            ]
        else:
            gen_inflation = self.plant_config["finance_parameters"]["profast_general_inflation"]

        land_cost = 0.0

        params = {}
        params.setdefault(
            "commodity",
            {
                "name": self.options["commodity_type"].capitalize(),
                "unit": "kg" if self.options["commodity_type"] in mass_commodities else "kWh",
                "initial price": 100,
                "escalation": gen_inflation,
            },
        )

        if self.options["commodity_type"] != "co2":
            params.setdefault(
                "capacity",
                float(inputs[f"total_{self.options['commodity_type']}_produced"][0]) / 365.0,
            )
        else:
            params.setdefault(
                "capacity",
                float(inputs["co2_capture_kgpy"]) / 365.0,
            )

        params.setdefault("long term utilization", 1)  # TODO considering using utilization

        if "pf_params" in self.plant_config["finance_parameters"]:
            pf_params = self.plant_config["finance_parameters"]["pf_params"]["params"]
            avoided_params = ["capacity", "commodity", "long term utilization"]
            pf_params = {k: v for k, v in pf_params.items() if k not in avoided_params}
            params.update(pf_params)

        else:
            params.setdefault("maintenance", {"value": 0, "escalation": gen_inflation})
            params.setdefault(
                "installation cost",
                {
                    "value": 0,
                    "depr type": "Straight line",
                    "depr period": 4,
                    "depreciable": False,
                },
            )
            if land_cost > 0:
                params.setdefault("non depr assets", land_cost)
                params.setdefault(
                    "end of proj sale non depr assets",
                    land_cost * (1 + gen_inflation) ** self.plant_config["plant"]["plant_life"],
                )
            params.setdefault("demand rampup", 0)
            params.setdefault("credit card fees", 0)
            params.setdefault(
                "sales tax", self.plant_config["finance_parameters"]["sales_tax_rate"]
            )
            params.setdefault("license and permit", {"value": 00, "escalation": gen_inflation})
            params.setdefault("rent", {"value": 0, "escalation": gen_inflation})
            # TODO how to handle property tax and insurance for fully offshore?
            params.setdefault(
                "property tax and insurance",
                self.plant_config["finance_parameters"]["property_tax"]
                + self.plant_config["finance_parameters"]["property_insurance"],
            )
            params.setdefault(
                "admin expense",
                self.plant_config["finance_parameters"]["administrative_expense_percent_of_sales"],
            )
            params.setdefault(
                "total income tax rate",
                self.plant_config["finance_parameters"]["total_income_tax_rate"],
            )
            params.setdefault(
                "capital gains tax rate",
                self.plant_config["finance_parameters"]["capital_gains_tax_rate"],
            )
            params.setdefault("sell undepreciated cap", True)
            params.setdefault("tax losses monetized", True)
            params.setdefault("general inflation rate", gen_inflation)
            params.setdefault(
                "leverage after tax nominal discount rate",
                self.plant_config["finance_parameters"]["discount_rate"],
            )
            if self.plant_config["finance_parameters"]["debt_equity_split"]:
                params.setdefault(
                    "debt equity ratio of initial financing",
                    (
                        self.plant_config["finance_parameters"]["debt_equity_split"]
                        / (100 - self.plant_config["finance_parameters"]["debt_equity_split"])
                    ),
                )  # TODO this may not be put in right
            elif self.plant_config["finance_parameters"]["debt_equity_ratio"]:
                params.setdefault(
                    "debt equity ratio of initial financing",
                    (self.plant_config["finance_parameters"]["debt_equity_ratio"]),
                )  # TODO this may not be put in right
            params.setdefault("debt type", self.plant_config["finance_parameters"]["debt_type"])
            params.setdefault(
                "loan period if used", self.plant_config["finance_parameters"]["loan_period"]
            )
            params.setdefault(
                "debt interest rate",
                self.plant_config["finance_parameters"]["debt_interest_rate"],
            )
            params.setdefault(
                "cash onhand", self.plant_config["finance_parameters"]["cash_onhand_months"]
            )

        params.setdefault(
            "installation months",
            self.plant_config["plant"][
                "installation_time"
            ],  # Add installation time to yaml default=0
        )
        params.setdefault("operating life", self.plant_config["plant"]["plant_life"])
        params.setdefault(
            "analysis start year", self.plant_config["plant"]["financial_analysis_start_year"]
        )

        pf = ProFAST.ProFAST()
        for i in params:
            pf.set_params(i, params[i])

        # --------------------------------- Add capital and fixed items to ProFAST --------------
        for tech in self.tech_config:
            # tech_config is already filtered to include only relevant technologies
            if "electrolyzer" in tech:
                electrolyzer_refurbishment_schedule = np.zeros(
                    self.plant_config["plant"]["plant_life"]
                )

                refurb_period = round(float(inputs["time_until_replacement"][0]) / (24 * 365))
                electrolyzer_refurbishment_schedule[
                    refurb_period : self.plant_config["plant"]["plant_life"] : refurb_period
                ] = self.tech_config["electrolyzer"]["model_inputs"]["financial_parameters"][
                    "replacement_cost_percent"
                ]
                refurbishment_schedule = list(electrolyzer_refurbishment_schedule)
                depreciation_period = self.plant_config["finance_parameters"][
                    "depreciation_period_electrolyzer"
                ]
            else:
                refurbishment_schedule = [0]
                depreciation_period = self.plant_config["finance_parameters"]["depreciation_period"]

            pf.add_capital_item(
                name=f"{tech} System",
                cost=float(inputs[f"capex_adjusted_{tech}"][0]),
                depr_type=self.plant_config["finance_parameters"]["depreciation_method"],
                depr_period=depreciation_period,
                refurb=refurbishment_schedule,
            )
            pf.add_fixed_cost(
                name=f"{tech} O&M Cost",
                usage=1.0,
                unit="$/year",
                cost=float(inputs[f"opex_adjusted_{tech}"][0]),
                escalation=gen_inflation,
            )

        # ------------------------------------ solve and post-process -----------------------------

        sol = pf.solve_price()

        # Only hydrogen supported in the very short term
        if self.options["commodity_type"] == "hydrogen":
            outputs["LCOH"] = sol["price"]

        elif self.options["commodity_type"] == "nitrogen":
            outputs["LCON"] = sol["price"]

        elif self.options["commodity_type"] == "ammonia":
            outputs["LCOA"] = sol["price"]

        elif self.options["commodity_type"] == "electricity":
            outputs["LCOE"] = sol["price"]

        elif self.options["commodity_type"] == "co2":
            outputs["LCOC"] = sol["price"]
