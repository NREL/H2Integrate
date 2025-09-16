import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig
from h2integrate.core.validators import gt_zero, range_val


@define
class SimpleLCOFinanceConfig(BaseConfig):
    discount_rate: float = field(validator=range_val(0, 1))
    plant_life: int = field(converter=int, validator=gt_zero)


class SimpleLCOFinance(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)
        self.options.declare("commodity_type", types=str)
        self.options.declare("description", types=str, default="")

    def setup(self):
        if self.options["commodity_type"] == "electricity":
            commodity_units = "kW*h/year"
            lco_units = "USD/kW/h"
        else:
            commodity_units = "kg/year"
            lco_units = "USD/kg"

        LCO_base_str = f"LCO{self.options['commodity_type'][0].upper()}"
        self.output_txt = self.options["commodity_type"].lower()

        if self.options["description"] == "":
            self.LCO_str = LCO_base_str
        else:
            desc_str = self.options["description"].strip().strip("_()-")
            if desc_str == "":
                self.LCO_str = LCO_base_str
            else:
                self.output_txt = f"{self.options['commodity_type'].lower()}_{desc_str}"
                self.LCO_str = f"{LCO_base_str}_{desc_str}"

        self.add_output(self.LCO_str, val=0.0, units=lco_units)
        self.add_input(
            f"total_{self.options['commodity_type']}_produced",
            val=0.0,
            units=commodity_units,
        )
        tech_config = self.tech_config = self.options["tech_config"]
        for tech in tech_config:
            self.add_input(f"capex_adjusted_{tech}", val=0.0, units="USD")
            self.add_input(f"opex_adjusted_{tech}", val=0.0, units="USD/year")

        if "electrolyzer" in tech_config:
            self.add_input("electrolyzer_time_until_replacement", units="h")

        finance_config = self.options["plant_config"]["finance_parameters"]["model_inputs"]
        finance_config.update({"plant_life": self.options["plant_config"]["plant"]["plant_life"]})

        self.config = SimpleLCOFinanceConfig.from_dict(finance_config)
        self.add_output(
            f"annual_replacement_costs_{self.output_txt}",
            val=0.0,
            shape=self.config.plant_life,
            units="USD",
        )
        self.add_output(f"total_capital_cost_{self.output_txt}", val=0.0, units="USD")
        self.add_output(
            f"annual_fixed_costs_{self.output_txt}",
            val=0.0,
            shape=self.config.plant_life,
            units="USD",
        )

    def compute(self, inputs, outputs):
        annual_output = float(inputs[f"total_{self.options['commodity_type']}_produced"][0])

        total_capex = 0
        total_fixed_om = 0
        replacement_costs_per_year = np.zeros(self.config.plant_life)

        for tech in self.tech_config:
            tech_model_inputs = self.tech_config[tech].get("model_inputs")
            if tech_model_inputs is None:
                continue  # Skip this tech if no model_inputs
            one_time_capital_cost = float(inputs[f"capex_adjusted_{tech}"][0])
            fixed_om_cost_per_year = float(inputs[f"opex_adjusted_{tech}"][0])

            total_capex += one_time_capital_cost
            total_fixed_om += fixed_om_cost_per_year

            tech_capex_info = tech_model_inputs.get("financial_parameters", {}).get(
                "capital_items", {}
            )
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
                # add refurbishment schedule to tech-specific capital item entry
                # tech_capex_info["refurb"] = list(refurb_schedule)
                tech_replacement_cost = refurb_schedule * one_time_capital_cost
                replacement_costs_per_year += tech_replacement_cost

        annual_production = np.zeros(self.config.plant_life)
        annual_OM = np.zeros(self.config.plant_life)
        annual_replacement_costs = np.zeros(self.config.plant_life)
        for y in range(self.config.plant_life):
            denom = (1 + self.config.discount_rate) ** y
            annual_production[y] = annual_output / denom
            annual_OM[y] = total_fixed_om / denom
            annual_replacement_costs[y] = replacement_costs_per_year[y] / denom

        total_annual_costs = annual_OM + annual_replacement_costs
        lco = (total_capex + np.sum(total_annual_costs)) / np.sum(annual_production)
        outputs[self.LCO_str] = lco
        outputs[f"annual_replacement_costs_{self.output_txt}"] = annual_replacement_costs
        outputs[f"total_capital_cost_{self.output_txt}"] = total_capex
        outputs[f"annual_fixed_costs_{self.output_txt}"] = annual_OM
