from pathlib import Path

import attrs
import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import (
    BaseConfig,
    attr_serializer,
    attr_hopp_filter,
    dict_to_yaml_formatting,
    check_plant_config_and_profast_params,
)
from h2integrate.core.dict_utils import update_defaults
from h2integrate.core.validators import gt_zero, contains, gte_zero, range_val
from h2integrate.tools.profast_tools import run_profast, create_and_populate_profast
from h2integrate.core.inputs.validation import write_yaml
from h2integrate.tools.profast_reverse_tools import convert_pf_to_dict


finance_to_pf_param_mapper = {
    # "income tax rate": "total income tax rate",
    "debt equity ratio": "debt equity ratio of initial financing",
    "discount rate": "leverage after tax nominal discount rate",
    "plant life": "operating life",
    "sales tax rate": "sales tax",
    "cash onhand months": "cash onhand",
    "topc": "TOPC",
    "installation time": "installation months",
    "inflation rate": "general inflation rate",
}


def check_param_format(param_dict):
    param_dict_reformatted = {}
    for k, v in param_dict.items():
        k_new = k.replace(" ", "_")
        if isinstance(v, dict):
            v_new = {vk.replace("_", " "): vv for vk, vv in v.items()}
            param_dict_reformatted[k_new] = v_new
        else:
            param_dict_reformatted[k_new] = v
    return param_dict_reformatted


@define
class BasicProFASTParameterConfig(BaseConfig):
    """Financing parameters for ProFAST

    Attributes:
        plant_life (int): operating life of plant in years
        analysis_start_year (int): calendar year to start financial analysis
        installation_time (int): time between `analysis_start_year` and operation start in months
        discount_rate (float): leverage after tax nominal discount rate
        debt_equity_ratio (float): debt to equity ratio of initial financing.
        property_tax_and_insurance (float): property tax and insurance
        total_income_tax_rate (float): income tax rate
        capital_gains_tax_rate (float): tax rate fraction on capital gains
        sales_tax_rate (float): sales tax fraction
        debt_interest_rate (float): interest rate on debt
        inflation_rate (float): escalation rate. Set to zero for a nominal analysis.
        cash_onhand_months (int): number of months with cash onhand.
        admin_expense (float): adminstrative expense as a fraction of sales

        non_depr_assets (float): cost (in `$`) of nondepreciable assets, such as land.
        end_of_proj_sale_non_depr_assets (float): cost (in `$`) of nondepreciable assets
            that are sold at the end of the project.

        Optional:
        tax_loss_carry_forward_years (int, optional):
        tax_losses_monetized (bool, optional):
        sell_undepreciated_cap (bool, optional):
        credit_card_fees (float, optional):
        demand_rampup (float, optional):
        debt_type (str, optional):
        loan_period_if_used (int, optional)
        commodity (dict, optional):
        installation_cost  (dict, optional):
        topc (dict, optional):
        annual_operating_incentive (dict, optional):
        incidental_revenue (dict, optional):
        road_tax (dict, optional):
        labor (dict, optional):
        maintenance (dict, optional):
        rent (dict, optional):
        license_and_permit (dict, optional):
        one_time_cap_inct (dict, optional):

    Returns:
        _type_: _description_
    """

    plant_life: int = field(converter=int, validator=gte_zero)
    analysis_start_year: int = field(converter=int, validator=range_val(1000, 4000))
    installation_time: int = field(converter=int, validator=gte_zero)

    discount_rate: float = field(validator=range_val(0, 1))
    debt_equity_ratio: float = field(validator=gt_zero)
    property_tax_and_insurance: float = field(validator=range_val(0, 1))

    total_income_tax_rate: float = field(validator=range_val(0, 1))
    capital_gains_tax_rate: float = field(validator=range_val(0, 1))
    sales_tax_rate: float = field(validator=range_val(0, 1))
    debt_interest_rate: float = field(validator=range_val(0, 1))

    # TODO: see if folks want this to be just 'inflation rate'
    inflation_rate: float = field(validator=range_val(0, 1))

    cash_onhand_months: int = field(converter=int)  # int?

    admin_expense: float = field(validator=range_val(0, 1))

    non_depr_assets: float = field(default=0.0, validator=gte_zero)
    end_of_proj_sale_non_depr_assets: float = field(default=0.0, validator=gte_zero)

    tax_loss_carry_forward_years: int = field(default=0, validator=gte_zero)
    tax_losses_monetized: bool = field(default=True)
    sell_undepreciated_cap: bool = field(default=True)

    credit_card_fees: float = field(default=0.0)
    demand_rampup: float = field(default=0.0, validator=gte_zero)

    debt_type: str = field(
        default="Revolving debt", validator=contains(["Revolving debt", "One time loan"])
    )
    loan_period_if_used: int = field(default=0, validator=gte_zero)

    commodity: dict = field(
        default={
            "name": None,
            "unit": None,
            "inital price": 100,
            "escalation": 0.0,
        }
    )

    installation_cost: dict = field(
        default={
            "value": 0.0,
            "depr type": "Straight line",
            "depr period": 4,
            "depreciable": False,
        }
    )
    topc: dict = field(
        default={
            "unit price": 0.0,
            "decay": 0.0,
            "sunset years": 0,
            "support utilization": 0.0,
        }
    )

    annual_operating_incentive: dict = field(
        default={
            "value": 0.0,
            "decay": 0.0,
            "sunset years": 0,
            "taxable": True,
        }
    )
    incidental_revenue: dict = field(default={"value": 0.0, "escalation": 0.0})
    road_tax: dict = field(default={"value": 0.0, "escalation": 0.0})
    labor: dict = field(default={"value": 0.0, "rate": 0.0, "escalation": 0.0})
    maintenance: dict = field(default={"value": 0.0, "escalation": 0.0})
    rent: dict = field(default={"value": 0.0, "escalation": 0.0})
    license_and_permit: dict = field(default={"value": 0.0, "escalation": 0.0})
    one_time_cap_inct: dict = field(
        default={"value": 0.0, "depr type": "MACRS", "depr period": 3, "depreciable": False}
    )

    def as_dict(self) -> dict:
        """Creates a JSON and YAML friendly dictionary that can be save for future reloading.


        Returns:
            dict: All key, value pairs required for class re-creation.
        """
        pf_params_init = attrs.asdict(
            self, filter=attr_hopp_filter, value_serializer=attr_serializer
        )

        # rename keys to profast format
        pf_params = {k.replace("_", " "): v for k, v in pf_params_init.items()}

        # update all instances of "escalation" with the general inflation rate
        pf_params = update_defaults(pf_params, "escalation", self.inflation_rate)

        # rename keys
        params = {}
        for keyname, vals in pf_params.copy().items():
            if keyname in finance_to_pf_param_mapper:
                params[finance_to_pf_param_mapper[keyname]] = vals
            else:
                params[keyname] = vals
        return params

    def create_years_of_operation(self):
        operation_start_year = self.analysis_start_year + (self.installation_time / 12)
        years_of_operation = np.arange(
            int(operation_start_year), int(operation_start_year + self.plant_life), 1
        )
        year_keys = [f"{y}" for y in years_of_operation]
        return year_keys


@define
class ProFASTDefaultCapitalItem(BaseConfig):
    depr_period: int = field(converter=int, validator=contains([3, 5, 7, 10, 15, 20]))
    depr_type: str = field(converter=str.strip, validator=contains(["MACRS", "Straight line"]))
    refurb: int | float | list[float] = field(default=[0.0])
    replacement_cost_percent: int | float = field(default=0.0, validator=range_val(0, 1))

    def create_dict(self):
        non_profast_attrs = ["replacement_cost_percent"]
        full_dict = self.as_dict()
        d = {k: v for k, v in full_dict.items() if k not in non_profast_attrs}
        return d


@define
class ProFASTDefaultFixedCost(BaseConfig):
    escalation: float | int = field()
    unit: str = field(default="$/year")
    usage: float | int = field(default=1.0)

    def create_dict(self):
        return self.as_dict()


@define
class ProFASTDefaultIncentive(BaseConfig):
    decay: float | int = field()
    sunset_years: int = field(default=10, converter=int)
    tax_credit: bool = field(default=True)

    def create_dict(self):
        return self.as_dict()


class ProFastComp(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)
        self.options.declare("commodity_type", types=str)

    def setup(self):
        if self.options["commodity_type"] == "electricity":
            commodity_units = "kW*h/year"
            lco_units = "USD/kW/h"
        else:
            commodity_units = "kg/year"
            lco_units = "USD/kg"

        self.LCO_str = f"LCO{self.options['commodity_type'][0].upper()}"
        self.add_output(self.LCO_str, val=0.0, units=lco_units)

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

        if "electrolyzer" in tech_config:
            self.add_input("time_until_replacement", units="h")

        plant_config = self.options["plant_config"]

        finance_params = plant_config["finance_parameters"]["model_inputs"]["params"]

        # make consistent formatting
        fin_params = {k.replace("_", " "): v for k, v in finance_params.items()}
        # check for duplicated entries (ex. 'analysis_start_year' and 'analysis start year')
        if len(fin_params) != len(finance_params):
            finance_keys = [k.replace("_", " ") for k, v in finance_params.items()]
            fin_keys = list(fin_params.keys())
            duplicated_entries = [k for k in fin_keys if finance_keys.count(k) > 1]
            err_info = "\n".join(
                f"{d}: both `{d}` and `{d.replace('_','')}` map to {d}" for d in duplicated_entries
            )
            # NOTE: not an issue if both values are the same,
            # but better to inform users earlier on to prevent accidents
            for d in duplicated_entries:
                err_info += f"{d}: both `{d}` and `{d.replace(' ','_')}` map to {d}"
            msg = (
                f"Duplicate entries found in ProFastComp params. Duplicated entries are: {err_info}"
            )
            raise ValueError(msg)

        # check if duplicate entries were input, like "installation time" AND "installation months"
        for nickname, realname in finance_to_pf_param_mapper.items():
            has_nickname = any(k == nickname for k, v in fin_params.items())
            has_realname = any(k == realname for k, v in fin_params.items())
            # check for duplicate entries
            if has_nickname and has_realname:
                check_plant_config_and_profast_params(fin_params, fin_params, nickname, realname)
        # check for value mismatch
        if "operating life" in fin_params:
            check_plant_config_and_profast_params(
                plant_config["plant"], fin_params, "plant_life", "operating life"
            )

        # if profast params are in profast format
        if any(k in list(finance_to_pf_param_mapper.values()) for k, v in fin_params.items()):
            pf_param_to_finance_mapper = {v: k for k, v in finance_to_pf_param_mapper.items()}
            pf_params = {}
            for k, v in fin_params.items():
                if k.replace("_", " ") in pf_param_to_finance_mapper:
                    pf_params[pf_param_to_finance_mapper[k]] = v
                else:
                    pf_params[k] = v
            fin_params = dict(pf_params.items())

        fin_params = check_param_format(fin_params)

        fin_params.update({"plant_life": plant_config["plant"]["plant_life"]})
        # initialize financial parameters
        self.params = BasicProFASTParameterConfig.from_dict(fin_params)

        # initialize default capital item parameters
        capital_item_params = plant_config["finance_parameters"]["model_inputs"].get(
            "capital_items", {}
        )
        self.capital_item_settings = ProFASTDefaultCapitalItem.from_dict(capital_item_params)

        # initialize default fixed cost parameters
        fixed_cost_params = plant_config["finance_parameters"]["model_inputs"].get(
            "fixed_costs", {}
        )
        fixed_cost_params.setdefault("escalation", self.params.inflation_rate)
        self.fixed_cost_settings = ProFASTDefaultFixedCost.from_dict(fixed_cost_params)

        # incentives - unused for now
        # incentive_params = plant_config["finance_parameters"]["model_inputs"].get(
        #     "incentives", {}
        # )
        # incentive_params.setdefault("decay", -1 * self.params.inflation_rate)
        # self.incentive_params_settings = ProFASTDefaultIncentive.from_dict(incentive_params)

    def compute(self, inputs, outputs):
        mass_commodities = ["hydrogen", "ammonia", "co2", "nitrogen"]

        # update parameters with commodity, capacity, and utilization
        profast_params = self.params.as_dict()
        profast_params["commodity"].update({"name": self.options["commodity_type"]})
        profast_params["commodity"].update(
            {"unit": "kg" if self.options["commodity_type"] in mass_commodities else "kWh"}
        )

        if self.options["commodity_type"] != "co2":
            capacity = float(inputs[f"total_{self.options['commodity_type']}_produced"][0]) / 365.0
        else:
            capacity = float(inputs["co2_capture_kgpy"]) / 365.0
        profast_params["capacity"] = capacity  # TODO: update to actual daily capacity
        profast_params["long term utilization"] = 1  # TODO: update to capacity factor

        # initialize profast dictionary
        pf_dict = {"params": profast_params, "capital_items": {}, "fixed_costs": {}}

        # initialize dictionary of capital items and fixed costs
        capital_items = {}
        fixed_costs = {}

        # create default capital item and fixed cost entries
        capital_item_defaults = self.capital_item_settings.create_dict()
        fixed_cost_defaults = self.fixed_cost_settings.create_dict()

        # loop through technologies and create cost entries
        for tech in self.tech_config:
            # get tech-specific capital item parameters
            tech_capex_info = (
                self.tech_config[tech]["model_inputs"]
                .get("financial_parameters", {})
                .get("capital_items", {})
            )

            # add CapEx cost to tech-specific capital item entry
            tech_capex_info.update({"cost": float(inputs[f"capex_adjusted_{tech}"][0])})

            # see if any refurbishment information was input
            if "replacement_cost_percent" in tech_capex_info:
                refurb_schedule = np.zeros(self.params.plant_life)

                if "refurbishment_period_years" in tech_capex_info:
                    refurb_period = tech_capex_info["refurbishment_period_years"]
                else:
                    # TODO: make below tech specific
                    refurb_period = round(float(inputs["time_until_replacement"][0]) / (24 * 365))

                refurb_schedule[refurb_period : self.params.plant_life : refurb_period] = (
                    tech_capex_info["replacement_cost_percent"]
                )
                # add refurbishment schedule to tech-specific capital item entry
                tech_capex_info["refurb"] = list(refurb_schedule)

            # update any unset capital item parameters with the default values
            for cap_item_key, cap_item_val in capital_item_defaults.items():
                tech_capex_info.setdefault(cap_item_key, cap_item_val)
            capital_items[tech] = tech_capex_info

            # get tech-specific fixed cost parameters
            tech_opex_info = (
                self.tech_config[tech]["model_inputs"]
                .get("financial_parameters", {})
                .get("fixed_costs", {})
            )

            # add CapEx cost to tech-specific fixed cost entry
            tech_opex_info.update({"cost": float(inputs[f"opex_adjusted_{tech}"][0])})

            # update any unset fixed cost parameters with the default values
            for fix_cost_key, fix_cost_val in fixed_cost_defaults.items():
                tech_opex_info.setdefault(fix_cost_key, fix_cost_val)
            fixed_costs[tech] = tech_opex_info

        # add capital costs and fixed costs to pf_dict
        pf_dict["capital_items"] = capital_items
        pf_dict["fixed_costs"] = fixed_costs
        # create ProFAST object
        pf = create_and_populate_profast(pf_dict)
        # simulate ProFAST
        sol, summary, price_breakdown = run_profast(pf)

        # Check whether to export profast object to .yaml file
        if self.options["plant_config"]["finance_parameters"]["model_inputs"].get(
            "save_profast_to_file", False
        ):
            output_dir = self.options["driver_config"]["general"]["folder_output"]
            fdesc = self.options["plant_config"]["finance_parameters"]["model_inputs"][
                "profast_output_description"
            ]
            fname = f"{fdesc}_{self.options['commodity_type']}.yaml"
            fpath = Path(output_dir) / fname
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            d = convert_pf_to_dict(pf)
            d = dict_to_yaml_formatting(d)
            write_yaml(d, fpath)

        outputs[self.LCO_str] = sol["price"]  # TODO: replace with sol['lco']
