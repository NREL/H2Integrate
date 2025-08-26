import openmdao.api as om
import numpy_financial as npf


class AdjustedCapexOpexComp(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("tech_config", types=dict)
        self.options.declare("plant_config", types=dict)

    def setup(self):
        tech_config = self.options["tech_config"]
        plant_config = self.options["plant_config"]
        self.inflation_rate = plant_config["finance_parameters"]["cost_adjustment_parameters"][
            "cost_year_adjustment_inflation"
        ]
        self.target_dollar_year = plant_config["finance_parameters"]["cost_adjustment_parameters"][
            "target_dollar_year"
        ]

        # Ensure all technologies have a discount year set; use cost year if not specified
        for tech in tech_config:
            if tech not in self.discount_years:
                self.discount_years[tech] = self.cost_year

        for tech in tech_config:
            self.add_input(f"capex_{tech}", val=0.0, units="USD")
            self.add_input(f"opex_{tech}", val=0.0, units="USD/year")
            self.add_discrete_input(f"cost_year_{tech}", val=0, desc="Dollar year for costs")

            self.add_output(f"capex_adjusted_{tech}", val=0.0, units="USD")
            self.add_output(f"opex_adjusted_{tech}", val=0.0, units="USD/year")

        self.add_output("total_capex_adjusted", val=0.0, units="USD")
        self.add_output("total_opex_adjusted", val=0.0, units="USD/year")

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        total_capex_adjusted = 0.0
        total_opex_adjusted = 0.0
        for tech in self.options["tech_config"]:
            capex = float(inputs[f"capex_{tech}"][0])
            opex = float(inputs[f"opex_{tech}"][0])
            cost_year = int(discrete_inputs[f"cost_year_{tech}"])
            periods = self.target_dollar_year - cost_year
            adjusted_capex = -npf.fv(self.inflation_rate, periods, 0.0, capex)
            adjusted_opex = -npf.fv(self.inflation_rate, periods, 0.0, opex)
            outputs[f"capex_adjusted_{tech}"] = adjusted_capex
            outputs[f"opex_adjusted_{tech}"] = adjusted_opex
            total_capex_adjusted += adjusted_capex
            total_opex_adjusted += adjusted_opex

        outputs["total_capex_adjusted"] = total_capex_adjusted
        outputs["total_opex_adjusted"] = total_opex_adjusted
