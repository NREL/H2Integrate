from pathlib import Path

import numpy as np
import pandas as pd
import openmdao.api as om
import numpy_financial as npf
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, check_plant_config_and_profast_params
from h2integrate.core.validators import gte_zero, range_val


@define
class NPVFinancialConfig(BaseConfig):
    """Config of financing parameters for NPVFinancial.

    Attributes:
        plant_life (int): operating life of plant in years
        discount_rate (float): leverage after tax nominal discount rate
        commodity_sell_price (int | float, optional): sell price of commodity in
            USD/unit of commodity. Defaults to 0.0
        save_cost_breakdown (bool, optional): whether to save the cost breakdown per year.
            Defaults to False.
        save_npv_breakdown (bool, optional): whether to save the npv breakdown per technology.
            Defaults to False.
        cost_breakdown_file_description (str, optional): description to include in filename of
            cost breakdown file or npv breakdown file if either ``save_cost_breakdown`` or
            ``save_npv_breakdown`` is True. Defaults to 'default'.
    """

    plant_life: int = field(converter=int, validator=gte_zero)
    discount_rate: float = field(validator=range_val(0, 1))
    commodity_sell_price: int | float = field(default=0.0)
    save_cost_breakdown: bool = field(default=False)
    save_npv_breakdown: bool = field(default=False)
    cost_breakdown_file_description: str = field(default="default")


class NPVFinancial(om.ExplicitComponent):
    """_summary_

    Args:
        om (_type_): _description_

        https://numpy.org/numpy-financial/latest/npv.html#numpy_financial.npv:
        "By convention, investments or “deposits” are negative,
        income or “withdrawals” are positive; values must begin with the
        initial investment, thus values[0] will typically be negative."
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)
        self.options.declare("commodity_type", types=str)
        self.options.declare("description", types=str, default="")

    def setup(self):
        if (
            self.options["description"] == ""
            or self.options["description"] == self.options["commodity_type"]
        ):
            self.NPV_str = f"{self.options['commodity_type']}_NPV"
        else:
            NPV_base_str = f"{self.options['commodity_type']}"
            NPV_desc_str = (
                self.options["description"]
                .replace(self.options["commodity_type"], "")
                .strip()
                .strip("_()-")
            )
            if NPV_desc_str == "":
                self.NPV_str = f"{NPV_base_str}_NPV"
            else:
                self.NPV_str = f"{NPV_base_str}_{NPV_desc_str}_NPV"

        # TODO: update below with standardized naming
        if self.options["commodity_type"] == "electricity":
            commodity_units = "kW*h/year"
        else:
            commodity_units = "kg/year"

        self.add_output(self.NPV_str, val=0.0, units="USD")

        if self.options["commodity_type"] == "co2":
            self.add_input("co2_capture_kgpy", val=0.0, units="kg/year")
        else:
            self.add_input(
                f"total_{self.options['commodity_type']}_produced",
                val=0.0,
                units=commodity_units,
            )

        tech_config = self.tech_config = self.options["tech_config"]
        for tech in tech_config:
            self.add_input(f"capex_adjusted_{tech}", val=0.0, units="USD")
            self.add_input(f"opex_adjusted_{tech}", val=0.0, units="USD/year")

        # TODO: update below with standardized naming
        if "electrolyzer" in tech_config:
            self.add_input("electrolyzer_time_until_replacement", units="h")

        plant_config = self.options["plant_config"]
        finance_params = plant_config["finance_parameters"]["model_inputs"]
        if "plant_life" in finance_params:
            check_plant_config_and_profast_params(
                plant_config["plant"], finance_params, "plant_life", "plant_life"
            )
        finance_params.update({"plant_life": plant_config["plant"]["plant_life"]})
        self.config = NPVFinancialConfig.from_dict(finance_params)

    def compute(self, inputs, outputs):
        sign_of_costs = -1

        # TODO: update below for standardized naming and also variable simulation lengths
        if self.options["commodity_type"] != "co2":
            annual_production = float(inputs[f"total_{self.options['commodity_type']}_produced"][0])
        else:
            annual_production = float(inputs["co2_capture_kgpy"])

        income = self.config.commodity_sell_price * annual_production
        cash_inflow = np.concatenate(([0], income * np.ones(self.config.plant_life)))
        cost_breakdown = {f"Cash Inflow of Selling {self.options['commodity_type']}": cash_inflow}
        initial_investment_cost = 0
        for tech in self.tech_config:
            capex = sign_of_costs * float(inputs[f"capex_adjusted_{tech}"][0])
            fixed_om = sign_of_costs * float(inputs[f"opex_adjusted_{tech}"][0])

            capex_per_year = np.zeros(int(self.config.plant_life + 1))
            capex_per_year[0] = capex
            initial_investment_cost += capex

            cost_breakdown[f"{tech}: capital cost"] = capex_per_year
            cost_breakdown[f"{tech}: fixed o&m"] = np.concatenate(
                ([0], fixed_om * np.ones(self.config.plant_life))
            )

            # get tech-specific capital item parameters
            tech_capex_info = (
                self.tech_config[tech]["model_inputs"]
                .get("financial_parameters", {})
                .get("capital_items", {})
            )

            # see if any refurbishment information was input
            if "replacement_cost_percent" in tech_capex_info:
                refurb_schedule = np.zeros(self.config.plant_life)

                if "refurbishment_period_years" in tech_capex_info:
                    refurb_period = tech_capex_info["refurbishment_period_years"]
                else:
                    refurb_period = round(
                        float(inputs[f"{tech}_time_until_replacement"][0]) / (24 * 365)
                    )

                refurb_schedule[refurb_period : self.config.plant_life : refurb_period] = (
                    tech_capex_info["replacement_cost_percent"]
                )

                refurb_cost = capex * refurb_schedule
                # add refurbishment schedule to tech-specific capital item entry
                cost_breakdown[f"{tech}: replacement cost"] = refurb_cost

        total_costs = [np.array(v) for k, v in cost_breakdown.items()]
        cash_outflows = np.array(total_costs).sum(axis=0)
        npf.npv(self.config.discount_rate, cash_outflows)

        npv_item_check = 0
        npv_cost_breakdown = {}
        for cost_type, cost_vals in cost_breakdown.items():
            npv_item = npf.npv(self.config.discount_rate, cost_vals)
            npv_item_check += float(npv_item)
            npv_cost_breakdown[cost_type] = float(npv_item)

        if self.config.save_cost_breakdown or self.config.save_npv_breakdown:
            output_dir = self.options["driver_config"]["general"]["folder_output"]
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            fdesc = self.config.cost_breakdown_file_description

            if (
                self.options["description"] == ""
                or self.options["description"] == self.options["commodity_type"]
            ):
                filename_base = f"{fdesc}_{self.options['commodity_type']}_NPVFinancial"
            else:
                desc = (
                    self.NPV_str.replace("_NPV", "")
                    .replace(self.options["commodity_type"], "")
                    .strip("_")
                )
                filename_base = f"{fdesc}_{self.options['commodity_type']}_{desc}_NPVFinancial"
            if self.config.save_npv_breakdown:
                npv_fname = f"{filename_base}_NPV_breakdown.csv"
                npv_fpath = Path(output_dir) / npv_fname
                npv_breakdown = pd.Series(npv_cost_breakdown)
                npv_breakdown.loc["Total"] = npv_item_check
                npv_breakdown.name = "NPV (USD)"
                npv_breakdown.to_csv(npv_fpath)

            if self.config.save_cost_breakdown:
                cost_fname = f"{filename_base}_cost_breakdown.csv"
                cost_fpath = Path(output_dir) / cost_fname

                annual_cost_breakdown = pd.DataFrame(cost_breakdown).T
                annual_cost_breakdown["Total cost (USD)"] = annual_cost_breakdown.sum(axis=1)
                annual_cost_breakdown.loc["Total cost per year (USD/year)"] = (
                    annual_cost_breakdown.sum(axis=0)
                )
                new_colnames = {f"Year {i}" for i in annual_cost_breakdown.columns.to_list()}
                annual_cost_breakdown = annual_cost_breakdown.rename(
                    columns=dict(zip(annual_cost_breakdown.columns.to_list(), new_colnames))
                )
                annual_cost_breakdown.to_csv(cost_fpath)

            outputs[self.NPV_str] = npv_item_check
