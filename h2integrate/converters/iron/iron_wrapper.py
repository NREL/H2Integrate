import copy
from pathlib import Path

from attrs import field, define
from hopp.utilities import load_yaml

import h2integrate.tools.profast_reverse_tools as rev_pf_tools
from h2integrate.core.utilities import CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains, range_val
from h2integrate.core.model_baseclasses import CostModelBaseClass
from h2integrate.simulation.technologies.iron.iron import run_iron_full_model
from h2integrate.simulation.technologies.iron.martin_transport.iron_transport import (
    calc_iron_ship_cost,
)


@define
class IronConfig(CostModelBaseConfig):
    # h2_kgpy: float = field()
    lcoe: float = field()  # $/MWh
    lcoh: float = field()  # $/kg
    winning_type: str = field(
        converter=(str.lower, str.strip), validator=contains(["h2", "ng"])
    )  # win
    post_type: str = field(
        converter=(str.lower, str.strip), validator=contains(["eaf", "none"])
    )  # post
    mine: str = field(
        validator=contains(["Hibbing", "Northshore", "United", "Minorca", "Tilden"])
    )  # ore
    taconite_pellet_type: str = field(
        converter=(str.lower, str.strip), validator=contains(["std", "drg"])
    )  # ore
    win_capacity_demon: str = field(
        default="iron", converter=(str.lower, str.strip), validator=contains(["iron", "steel"])
    )  # win
    iron_post_capacity: float | int = field(default=1000000)  # post
    iron_win_capacity: float | int = field(default=1418095)  # win
    ore_cf_estimate: float = field(default=0.9, validator=range_val(0, 1))  # cf


class IronComponent(CostModelBaseClass):
    """
    A simple OpenMDAO component that represents an Iron model from old GreenHEART code.

    This component uses caching to store and retrieve results of the iron model
    based on the configuration.
    """

    def setup(self):
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        self.config = IronConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost"),
            strict=False,
        )
        super().setup()

        CD = Path(__file__).parent
        old_input_path = CD / "old_input"
        h2i_config_old_fn = "h2integrate_config_modular.yaml"
        self.h2i_config_old = load_yaml(old_input_path / h2i_config_old_fn)

        self.add_output("iron_out", val=0.0, shape=n_timesteps, units="kg/h")

        self.add_input("lcoe", val=self.config.lcoe, units="USD/MW/h")
        self.add_input("lcoh", val=self.config.lcoh, units="USD/kg")

        self.add_output("total_iron_produced", val=0.0, units="kg/year")
        self.add_output("LCOI", val=0.0, units="USD/kg")

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # BELOW: Copy-pasted from ye olde h2integrate_simulation.py (the 1000+ line monster)

        iron_config = copy.deepcopy(self.h2i_config_old)

        # This is not the most graceful way to do this... but it avoids copied imports
        # and copying iron.py
        iron_ore_config = copy.deepcopy(iron_config)
        iron_win_config = copy.deepcopy(iron_config)
        iron_post_config = copy.deepcopy(iron_config)

        iron_ore_config["iron"] = iron_config["iron_ore"]
        iron_win_config["iron"] = iron_config["iron_win"]
        iron_post_config["iron"] = iron_config["iron_post"]
        for sub_iron_config in [
            iron_ore_config,
            iron_win_config,
            iron_post_config,
        ]:  # ,iron_post_config]: # iron_pre_config, iron_post_config
            sub_iron_config["iron"]["costs"]["lcoe"] = inputs["lcoe"][0] / 1e3
            sub_iron_config["iron"]["finances"]["lcoe"] = inputs["lcoe"][0] / 1e3
            sub_iron_config["iron"]["costs"]["lcoh"] = inputs["lcoh"][0]
            sub_iron_config["iron"]["finances"]["lcoh"] = inputs["lcoh"][0]

        # Update ore config
        iron_ore_config["iron"]["site"]["name"] = self.config.mine
        iron_ore_config["iron"]["performance"]["input_capacity_factor_estimate"] = (
            self.config.ore_cf_estimate
        )

        # Update win config
        iron_win_config["iron"]["product_selection"] = f"{self.config.winning_type}_dri"
        iron_win_config["iron"]["performance"]["plant_capacity_mtpy"] = (
            self.config.iron_win_capacity
        )

        # Update post config
        if self.config.post_type == "none":
            iron_post_config["iron"]["product_selection"] = "none"
        if self.config.post_type == "eaf":
            iron_post_config["iron"]["product_selection"] = f"{self.config.winning_type}_eaf"
            iron_post_config["iron"]["performance"]["capacity_denominator"] = (
                self.config.win_capacity_demon
            )
            iron_post_config["iron"]["performance"]["plant_capacity_mtpy"] = (
                self.config.iron_post_capacity
            )
        # TODO: find a way of looping the above and below
        iron_ore_performance, iron_ore_costs, iron_ore_finance = run_iron_full_model(
            iron_ore_config
        )

        # iron_pre_performance, iron_pre_costs, iron_pre_finance = \
        #     run_iron_full_model(iron_pre_config)

        iron_transport_cost_tonne, ore_profit_pct = calc_iron_ship_cost(iron_win_config)

        ### DRI ----------------------------------------------------------------------------
        if iron_win_config["iron"]["product_selection"] not in ["ng_dri", "h2_dri"]:
            raise ValueError(
                "The product selection for the iron win module must be either \
                'ng_dri' or 'h2_dri'"
            )

        iron_win_config["iron"]["finances"]["ore_profit_pct"] = ore_profit_pct
        iron_win_config["iron"]["costs"]["iron_transport_tonne"] = iron_transport_cost_tonne
        iron_win_config["iron"]["costs"]["lco_iron_ore_tonne"] = iron_ore_finance.sol["lco"]
        iron_win_performance, iron_win_costs, iron_win_finance = run_iron_full_model(
            iron_win_config
        )

        ### EAF ----------------------------------------------------------------------------
        if iron_post_config["iron"]["product_selection"] == "none":
            iron_performance = iron_win_performance
            iron_costs = iron_win_costs
            iron_finance = iron_win_finance

        else:
            if iron_post_config["iron"]["product_selection"] not in ["ng_eaf", "h2_eaf"]:
                raise ValueError(
                    "The product selection for the iron post module must be either \
                    'ng_eaf' or 'h2_eaf'"
                )
            pf_config = rev_pf_tools.make_pf_config_from_profast(
                iron_win_finance.pf
            )  # dictionary of profast objects
            pf_dict = rev_pf_tools.convert_pf_res_to_pf_config(
                copy.deepcopy(pf_config)
            )  # profast dictionary of values
            iron_post_config["iron"]["finances"]["pf"] = pf_dict
            iron_post_config["iron"]["costs"]["lco_iron_ore_tonne"] = iron_ore_finance.sol["lco"]

            iron_post_performance, iron_post_costs, iron_post_finance = run_iron_full_model(
                iron_post_config
            )

            iron_performance = iron_post_performance
            iron_costs = iron_post_costs
            iron_finance = iron_post_finance

        perf_df = iron_performance.performances_df
        iron_mtpy = perf_df.loc[perf_df["Name"] == "Pig Iron Production", "Model"].values[0]

        # ABOVE: Copy-pasted from ye olde h2integrate_simulation.py (the 1000+ line monster)

        outputs["iron_out"] = iron_mtpy * 1000 / 8760
        outputs["total_iron_produced"] = iron_mtpy * 1000

        cost_df = iron_costs.costs_df
        capex = 0
        opex = 0
        capex_list = [
            "EAF & Casting",
            "Shaft Furnace",
            "Reformer",
            "Recycle Compressor",
            "Oxygen Supply",
            "H2 Pre-heating",
            "Cooling Tower",
            "Piping",
            "Electrical & Instrumentation",
            "Buildings, Storage, Water Service",
            "Other Miscellaneous Cost",
        ]
        opex_list = [
            "labor_cost_annual_operation",
            "labor_cost_maintenance",
            "labor_cost_admin_support",
            "property_tax_insurance",
            "maintenance_materials",
        ]

        location = cost_df.columns.values[-1]
        for capex_item in capex_list:
            capex += cost_df.loc[cost_df["Name"] == capex_item, location].values[0]
        for opex_item in opex_list:
            opex += cost_df.loc[cost_df["Name"] == opex_item, location].values[0]

        outputs["CapEx"] = capex
        outputs["OpEx"] = opex

        lcoi = iron_finance.sol["lco"]
        outputs["LCOI"] = lcoi / 1000
