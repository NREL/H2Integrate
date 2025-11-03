from pathlib import Path

import numpy as np

from h2integrate.core.utilities import dict_to_yaml_formatting
from h2integrate.tools.profast_tools import (
    run_profast,
    make_price_breakdown,
    format_profast_price_breakdown_per_year,
)
from h2integrate.finances.profast_base import ProFastBase
from h2integrate.core.inputs.validation import write_yaml
from h2integrate.tools.profast_reverse_tools import convert_pf_to_dict


class ProFastLCO(ProFastBase):
    def add_model_specific_outputs(self):
        self.add_output(self.LCO_str, val=0.0, units=self.lco_units)
        self.outputs_to_units = {
            "wacc": "percent",
            "crf": "percent",
            "irr": "percent",
            "profit_index": "unitless",
            "investor_payback_period": "yr",
            "price": self.lco_units,
        }
        for output_var, units in self.outputs_to_units.items():
            self.add_output(f"{output_var}_{self.output_txt}", val=0.0, units=units)

        self.add_discrete_output(f"{self.LCO_str}_breakdown", val={}, desc="LCO Breakdown of costs")
        return

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pf = self.populate_profast(inputs)

        # simulate ProFAST
        sol, summary, price_breakdown = run_profast(pf)

        outputs[self.LCO_str] = sol["lco"]
        for output_var in self.outputs_to_units.keys():
            val = sol[output_var.replace("_", " ")]
            if isinstance(val, (np.ndarray, list, tuple)):  # only for IRR
                # if len(val)>0:
                val = val[-1]
            outputs[f"{output_var}_{self.output_txt}"] = val

        # make dictionary of ProFAST config
        pf_config_dict = convert_pf_to_dict(pf)

        # make LCO cost breakdown
        lco_breakdown, lco_check = make_price_breakdown(price_breakdown, pf_config_dict)
        discrete_outputs[f"{self.LCO_str}_breakdown"] = lco_breakdown

        # Check whether to export profast object to .yaml file
        save_results = self.options["plant_config"]["finance_parameters"]["model_inputs"].get(
            "save_profast_results", False
        )
        save_config = self.options["plant_config"]["finance_parameters"]["model_inputs"].get(
            "save_profast_config", False
        )

        if save_results or save_config:
            output_dir = self.options["driver_config"]["general"]["folder_output"]
            fdesc = self.options["plant_config"]["finance_parameters"]["model_inputs"].get(
                "profast_output_description", "ProFastComp"
            )

            fbasename = f"{fdesc}_{self.output_txt}"

            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            pf_config_dict = dict_to_yaml_formatting(pf_config_dict)

            if save_config:
                config_fpath = Path(output_dir) / f"{fbasename}_config.yaml"
                write_yaml(pf_config_dict, config_fpath)

            if save_results:
                price_breakdown_formatted = format_profast_price_breakdown_per_year(price_breakdown)
                pf_breakdown_fpath = Path(output_dir) / f"{fbasename}_profast_price_breakdown.csv"
                lco_breakdown_fpath = Path(output_dir) / f"{fbasename}_LCO_breakdown.yaml"
                price_breakdown_formatted.to_csv(pf_breakdown_fpath)
                lco_breakdown = dict_to_yaml_formatting(lco_breakdown)
                write_yaml(lco_breakdown, lco_breakdown_fpath)
