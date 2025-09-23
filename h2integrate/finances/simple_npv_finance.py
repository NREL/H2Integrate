from pathlib import Path

import numpy as np
import pandas as pd
import openmdao.api as om
import numpy_financial as npf
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, check_plant_config_and_profast_params
from h2integrate.core.validators import gte_zero, range_val


@define
class NPVFinanceConfig(BaseConfig):
    """Config of financing parameters for NPVFinance.

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


class NPVFinance(om.ExplicitComponent):
    """OpenMDAO component for calculating Net Present Value (NPV) of a plant or technology.

    This component computes the NPV of a given commodity-producing plant over its
    operational lifetime, accounting for capital expenditures (CAPEX), operating
    expenditures (OPEX), refurbishment/replacement costs, and commodity revenues.

    NPV is calculated using the discount rate and plant life defined in the
    `plant_config`. By convention, investments (CAPEX, OPEX, refurbishment) are
    treated as negative cash flows, while revenues from commodity sales are
    positive. This follows the NumPy Financial convention:

    Reference:
        https://numpy.org/numpy-financial/latest/npv.html#numpy_financial.npv

        * "By convention, investments or 'deposits' are negative, income or
        'withdrawals' are positive; values must begin with the initial
        investment, thus values[0] will typically be negative."

    Attributes:
        NPV_str (str): The dynamically generated name of the NPV output variable,
            based on `commodity_type` and optional `description`.
        tech_config (dict): Technology-specific configuration dictionary.
        config (NPVFinanceConfig): Parsed financial configuration parameters
            (e.g., discount rate, plant life, save options).
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

        plant_config = self.options["plant_config"]
        finance_params = plant_config["finance_parameters"]["model_inputs"]
        if "plant_life" in finance_params:
            check_plant_config_and_profast_params(
                plant_config["plant"], finance_params, "plant_life", "plant_life"
            )
        finance_params.update({"plant_life": plant_config["plant"]["plant_life"]})

        self.config = NPVFinanceConfig.from_dict(finance_params)

        tech_config = self.tech_config = self.options["tech_config"]
        for tech in tech_config:
            self.add_input(f"capex_adjusted_{tech}", val=0.0, units="USD")
            self.add_input(f"opex_adjusted_{tech}", val=0.0, units="USD/year")
            self.add_input(
                f"varopex_adjusted_{tech}",
                val=0.0,
                shape=plant_config["plant"]["plant_life"],
                units="USD/year",
            )

        # TODO: update below with standardized naming
        if "electrolyzer" in tech_config:
            self.add_input("electrolyzer_time_until_replacement", units="h")

        self.add_input(
            "commodity_sell_price", val=self.config.commodity_sell_price, units=commodity_units
        )

    def compute(self, inputs, outputs):
        """Compute the Net Present Value (NPV).

        Calculates discounted cash flows over the plant lifetime, accounting for:
            * Revenue from annual commodity production and sale.
            * CAPEX and OPEX for all technologies.
            * Replacement or refurbishment costs if provided.

        Optionally saves cost breakdowns and NPV breakdowns to CSV files if
        enabled in configuration.

        NPV that is positive indicates a profitable investment, while negative
        NPV indicates a loss.

        Args:
            inputs (dict-like): Dictionary of input values, including production,
                CAPEX, OPEX, and optional replacement periods.
            outputs (dict-like): Dictionary for storing computed outputs, including
                the NPV result.

        Produces:
            * `outputs[self.NPV_str]`: The total NPV in USD.

        Side Effects:
            * Writes annual cost breakdown and NPV breakdown CSVs to the configured
              output directory if `save_cost_breakdown` or `save_npv_breakdown`
              is enabled.

        Raises:
            FileNotFoundError: If the specified output directory cannot be created.
            ValueError: If refurbishment schedules cannot be derived from inputs.
        """
        # by convention, investments (capex, opex, refurbishment) are negative cash flows
        # have to add the correct sign convention for npf.npv function
        sign_of_costs = -1

        # TODO: update below for standardized naming and also variable simulation lengths
        if self.options["commodity_type"] != "co2":
            annual_production = float(inputs[f"total_{self.options['commodity_type']}_produced"][0])
        else:
            annual_production = float(inputs["co2_capture_kgpy"])

        income = float(inputs["commodity_sell_price"]) * annual_production
        cash_inflow = np.concatenate(([0], income * np.ones(self.config.plant_life)))
        cost_breakdown = {f"Cash Inflow of Selling {self.options['commodity_type']}": cash_inflow}
        initial_investment_cost = 0
        for tech in self.tech_config:
            capex = sign_of_costs * float(inputs[f"capex_adjusted_{tech}"])
            fixed_om = sign_of_costs * float(inputs[f"opex_adjusted_{tech}"])
            var_om = sign_of_costs * inputs[f"varopex_adjusted_{tech}"]

            capex_per_year = np.zeros(int(self.config.plant_life + 1))
            capex_per_year[0] = capex
            initial_investment_cost += capex

            cost_breakdown[f"{tech}: capital cost"] = capex_per_year
            cost_breakdown[f"{tech}: fixed o&m"] = np.concatenate(
                ([0], fixed_om * np.ones(self.config.plant_life))
            )
            cost_breakdown[f"{tech}: variable o&m"] = np.concatenate(([0], var_om))

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
        np.array(total_costs).sum(axis=0)

        npv_item_check = 0
        npv_cost_breakdown = {}
        for cost_type, cost_vals in cost_breakdown.items():
            npv_item = npf.npv(self.config.discount_rate, cost_vals)
            npv_item_check += float(npv_item)
            npv_cost_breakdown[cost_type] = float(npv_item)

        outputs[self.NPV_str] = npv_item_check

        if self.config.save_cost_breakdown or self.config.save_npv_breakdown:
            output_dir = self.options["driver_config"]["general"]["folder_output"]
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            fdesc = self.config.cost_breakdown_file_description

            if (
                self.options["description"] == ""
                or self.options["description"] == self.options["commodity_type"]
            ):
                filename_base = f"{fdesc}_{self.options['commodity_type']}_NPVFinance"
            else:
                desc = (
                    self.NPV_str.replace("_NPV", "")
                    .replace(self.options["commodity_type"], "")
                    .strip("_")
                )
                filename_base = f"{fdesc}_{self.options['commodity_type']}_{desc}_NPVFinance"
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
                new_colnames = {i: f"Year {i}" for i in annual_cost_breakdown.columns.to_list()}
                annual_cost_breakdown = annual_cost_breakdown.rename(columns=new_colnames)
                annual_cost_breakdown.to_csv(cost_fpath)
