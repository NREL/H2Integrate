import attrs
import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import (
    BaseConfig,
    attr_serializer,
    attr_hopp_filter,
    check_plant_config_and_profast_params,
)
from h2integrate.core.dict_utils import update_defaults, rename_dict_keys
from h2integrate.core.validators import gt_zero, contains, gte_zero, range_val
from h2integrate.tools.profast_tools import run_profast, create_and_populate_profast


finance_to_pf_param_mapper = {
    # "income tax rate": "total income tax rate",
    "debt equity ratio": "debt equity ratio of initial financing",
    "discount rate": "leverage after tax nominal discount rate",
    "plant life": "operating life",
    "sales tax rate": "sales tax",
    "cash onhand months": "cash onhand",
    "topc": "TOPC",
    "installation time": "installation months",
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
    """_summary_

    Attributes:
        plant_life (int): operating life of plant in years
        analysis_start_year (int): calendar year to start financial analysis
        installation_months (int): time between `analysis_start_year` and operation start in months
        discount_rate (float): leverage after tax nominal discount rate
        debt_equity_ratio (float): debt to equity ratio of initial financing.
        property_tax_and_insurance (float): property tax and insurance
        total_income_tax_rate (float): income tax rate
        capital_gains_tax_rate (float): tax rate fraction on capital gains
        sales_tax_rate (float): sales tax fraction
        debt_interest_rate (float): interest rate on debt
        general_inflation_rate (float): TODO: check name
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
    installation_months: int = field(converter=int, validator=gte_zero)

    discount_rate: float = field(validator=range_val(0, 1))
    debt_equity_ratio: float = field(validator=gt_zero)
    property_tax_and_insurance: float = field(validator=range_val(0, 1))

    total_income_tax_rate: float = field(validator=range_val(0, 1))
    capital_gains_tax_rate: float = field(validator=range_val(0, 1))
    sales_tax_rate: float = field(validator=range_val(0, 1))
    debt_interest_rate: float = field(validator=range_val(0, 1))

    # TODO: see if folks want this to be just 'inflation rate'
    general_inflation_rate: float = field(validator=range_val(0, 1))

    cash_onhand_months: int = field(converter=int)  # int?

    admin_expense: float = field(validator=range_val(0, 1))

    non_depr_assets: float = field(validator=gte_zero)
    end_of_proj_sale_non_depr_assets: float = field(validator=gte_zero)

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
            "iniital price": 100,
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
            "taxable": True,
        }
    )

    annual_operating_incentive: dict = field(
        default={
            "unit price": 0.0,
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
        pf_params = update_defaults(pf_params, "escalation", self.general_inflation_rate)

        # rename keys
        for keyname in pf_params.keys():
            if keyname in finance_to_pf_param_mapper:
                pf_params = rename_dict_keys(
                    pf_params, keyname, finance_to_pf_param_mapper[keyname]
                )
        return pf_params

    def create_years_of_operation(self):
        operation_start_year = self.analysis_start_year + (self.installation_months / 12)
        years_of_operation = np.arange(
            int(operation_start_year), int(operation_start_year + self.plant_life), 1
        )
        year_keys = [f"{y}" for y in years_of_operation]
        return year_keys


@define
class ProFASTDefaultCapitalItem(BaseConfig):
    depr_period: int = field(converter=int, validator=contains([3, 5, 7, 10, 15, 20]))
    depr_method: str = field(converter=str.strip, validator=contains(["MACRS", "Straight line"]))
    refurb: int | float | list[float] = field(default=[0.0])
    replacement_cost_percent: int | float = field(default=0.0, validator=range_val(0, 1))
    replacement_period_years: int | float = field(default=0.0)

    def create_dict(self):
        non_profast_attrs = ["replacement_cost_percent", "replacement_period_years"]
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
class ProFASTDefaultFeedstockCost(BaseConfig):
    escalation: float | int = field()
    unit: str = field(default="$/year")
    usage: float | int = field(default=1.0)
    feedstock_region: str = field(
        default="US Average",
        validator=contains(
            [
                "East North Central",
                "East South Central",
                "Middle Atlantic",
                "Mountain",
                "New England",
                "Pacific",
                "South Atlantic",
                "West North Central",
                "West South Central",
                "US Average",
            ]
        ),
    )

    def create_dict(self):
        non_profast_attrs = ["feedstock_region"]
        full_dict = self.as_dict()
        d = {k: v for k, v in full_dict.items() if k not in non_profast_attrs}
        return d


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
        self.LCO_str = f"LCO{self.options['commodity_type'][0].upper()}"
        if self.options["commodity_type"] == "electricity":
            commodity_units = "kW*h/year"
            lco_units = "USD/kW/h"
        else:
            commodity_units = "kg/year"
            lco_units = "USD/kg"

        if self.options["commodity_type"] == "co2":
            self.add_input("co2_capture_kgpy", val=0.0, units="kg/year")
        else:
            self.add_input(
                f"total_{self.options['commodity_type']}_produced",
                val=0.0,
                units=commodity_units,
            )
        self.add_output(self.LCO_str, val=0.0, units=lco_units)

        tech_config = self.tech_config = self.options["tech_config"]
        for tech in tech_config:
            self.add_input(f"capex_adjusted_{tech}", val=0.0, units="USD")
            self.add_input(f"opex_adjusted_{tech}", val=0.0, units="USD/year")

        if "electrolyzer" in tech_config:
            self.add_input("time_until_replacement", units="h")

        plant_config = self.options["plant_config"]

        fin_params = plant_config["finance_parameters"]["profast_inputs"]["params"]

        check_plant_config_and_profast_params(
            plant_config["plant"], fin_params, "plant_life", "operating_life"
        )
        check_plant_config_and_profast_params(
            plant_config["finance_parameters"],
            fin_params,
            "installation_time",
            "installation_months",
        )
        check_plant_config_and_profast_params(
            plant_config["finance_parameters"],
            fin_params,
            "analysis_start_year",
            "analysis_start_year",
        )

        fin_params.update(
            {
                "plant_life": plant_config["plant"]["plant_life"],
                "installation_time": plant_config["finance_parameters"]["installation_time"],
                "analysis_start_year": plant_config["finance_parameters"]["analysis_start_year"],
            }
        )

        fin_params = check_param_format(fin_params)
        self.params = BasicProFASTParameterConfig.from_dict(fin_params)

        capital_item_params = plant_config["finance_parameters"]["profast_inputs"].get(
            "capital_items", {}
        )
        self.capital_item_settings = ProFASTDefaultCapitalItem.from_dict(capital_item_params)

        fixed_cost_params = plant_config["finance_parameters"]["profast_inputs"].get(
            "fixed_costs", {}
        )
        fixed_cost_params.setdefault("escalation", self.params.general_inflation_rate)
        self.fixed_cost_settings = ProFASTDefaultFixedCost.from_dict(fixed_cost_params)

        # incentives - unused for now
        incentive_params = plant_config["finance_parameters"]["profast_inputs"].get(
            "incentives", {}
        )
        incentive_params.setdefault("decay", -1 * self.params.general_inflation_rate)
        self.incentive_params_settings = ProFASTDefaultIncentive.from_dict(incentive_params)

    def compute(self, inputs, outputs):
        mass_commodities = ["hydrogen", "ammonia", "co2", "nitrogen"]

        profast_params = self.params.as_dict()
        profast_params["commodity"].update({"name": self.options["commodity"]})
        profast_params["commodity"].update(
            {"unit": "kg" if self.options["commodity_type"] in mass_commodities else "kWh"}
        )
        profast_params["capacity"] = inputs["capacity_todo"]
        profast_params["long term utilization"] = inputs["utilization_todo"]

        pf_params = self.params.as_dict()
        pf_dict = {"params": pf_params, "capital_items": {}, "fixed_costs": {}}

        capital_items = {}
        fixed_costs = {}
        capital_item_defaults = self.capital_item_settings.create_dict()
        fixed_cost_defaults = self.fixed_cost_settings.create_dict()
        for tech in self.tech_config:
            tech_capex_info = (
                self.tech_config[tech]["model_inputs"]
                .get("financial_parameters", {})
                .get("capital_items", {})
            )
            tech_capex_info.update({"cost": float(inputs[f"capex_adjusted_{tech}"][0])})
            for cap_item_key, cap_item_val in capital_item_defaults:
                tech_capex_info.setdefault(cap_item_key, cap_item_val)
            capital_items[tech] = tech_capex_info

            tech_opex_info = (
                self.tech_config[tech]["model_inputs"]
                .get("financial_parameters", {})
                .get("fixed_costs", {})
            )
            tech_opex_info.update({"cost": float(inputs[f"opex_adjusted_{tech}"][0])})
            for fix_cost_key, fix_cost_val in fixed_cost_defaults:
                tech_opex_info.setdefault(fix_cost_key, fix_cost_val)
            fixed_costs[tech] = tech_opex_info

        pf = create_and_populate_profast(pf_dict)
        sol, summary, price_breakdown = run_profast(pf)

        outputs[self.LCO_str] = sol["price"]
