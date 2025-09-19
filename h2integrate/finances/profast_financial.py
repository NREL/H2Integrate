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
from h2integrate.tools.profast_tools import (
    run_profast,
    make_price_breakdown,
    create_years_of_operation,
    create_and_populate_profast,
    format_profast_price_breakdown_per_year,
)
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


def format_params_for_profast_config(param_dict):
    """Replace spaces with underscores for top-level dictionary keys and replace
    underscores with spaces for any embedded dictionaries. Create a dictionary that is
    formatted for BasicProFASTParameterConfig.


    Args:
        param_dict (dict): dictionary of financing parameters

    Returns:
        dict: financing parameters formatted for BasicProFASTParameterConfig
    """
    param_dict_reformatted = {}
    for k, v in param_dict.items():
        k_new = k.replace(" ", "_")
        if isinstance(v, dict):
            v_new = {vk.replace("_", " "): vv for vk, vv in v.items()}
            param_dict_reformatted[k_new] = v_new
        else:
            param_dict_reformatted[k_new] = v
    return param_dict_reformatted


def check_parameter_inputs(finance_params, plant_config):
    """Check and format the input finance parameters. This method checks:

    1) for duplicated keys that only differ in formatting (spaces or underscores).
        Such as 'analysis_start_year' and 'analysis start year'. Throws an error if found.
    2) two keys that map to the same parameter have differing values,
        see `finance_to_pf_param_mapper`. Such as 'installation time' and
        'installation months'. Throws an error if values differ.
    3) parameters that are in the ProFAST format are reformatted to be compatible with
        BasicProFASTParameterConfig

    Args:
        finance_params (dict): `params` dictionary containing financing information.
        plant_config (dict): plant configuration dictionary.

    Raises:
        ValueError: If duplicated keys are input.
        ValueError: If two equivalent keys have different values.

    Returns:
        dict: financing parameters formatted for BasicProFASTParameterConfig
        validated financing parameters with consistent formatting.
    """
    # make consistent formatting
    fin_params = {k.replace("_", " "): v for k, v in finance_params.items()}

    # check for duplicated entries (ex. 'analysis_start_year' and 'analysis start year')
    if len(fin_params) != len(finance_params):
        finance_keys = [k.replace("_", " ") for k, v in finance_params.items()]
        fin_keys = list(fin_params.keys())
        duplicated_entries = [k for k in fin_keys if finance_keys.count(k) > 1]
        # NOTE: not an issue if both values are the same,
        # but better to inform users earlier on to prevent accidents
        err_info = "\n".join(
            f"{d}: both `{d}` and `{d.replace('_','')}` map to {d}" for d in duplicated_entries
        )

        msg = f"Duplicate entries found in ProFastComp params. Duplicated entries are: {err_info}"
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

    fin_params = format_params_for_profast_config(fin_params)
    fin_params.update({"plant_life": plant_config["plant"]["plant_life"]})

    return fin_params


@define
class BasicProFASTParameterConfig(BaseConfig):
    """Config of financing parameters for ProFAST.

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
        admin_expense (float): administrative expense as a fraction of sales
        non_depr_assets (float, optional): cost (in `$`) of nondepreciable assets, such as land.
            Defaults to 0.
        end_of_proj_sale_non_depr_assets (float, optional): cost (in `$`) of nondepreciable assets
            that are sold at the end of the project. Defaults to 0.
        tax_loss_carry_forward_years (int, optional): Defaults to 0.
        tax_losses_monetized (bool, optional): Defaults to True.
        sell_undepreciated_cap (bool, optional): Defaults to True.
        credit_card_fees (float, optional): credit card fees as a fraction.
        demand_rampup (float, optional): Defaults to 0.
        debt_type (str, optional): must be either "Revolving debt" or "One time loan".
            Defaults to "Revolving debt".
        loan_period_if_used (int, optional): Loan period in years.
            Only used if `debt_type` is "One time loan". Defaults to 0.
        commodity (dict, optional):
        installation_cost  (dict, optional):
            - **value** (*float*): installation cost in USD. Defaults to 0.
            - **depr type** (*str*): either "Straight line" or "MACRS". Defaults to "Straight line"
            - **depr period** (*int*): depreciation period in years. Defaults to 4.
            - **depreciable** (*bool*): True if cost depreciates. Defaults to False.
        topc (dict, optional): take or pay contract.
        annual_operating_incentive (dict, optional):
        incidental_revenue (dict, optional):
        road_tax (dict, optional):
        labor (dict, optional):
        maintenance (dict, optional):
        rent (dict, optional):
        license_and_permit (dict, optional):
        one_time_cap_inct (dict, optional): investment tax credit.
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
            "initial price": 100,
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


@define
class ProFASTDefaultCapitalItem(BaseConfig):
    """Configuration class of default settings for ProFAST capital items.

    Attributes:
        depr_period (int): depreciation period in years if using MACRS depreciation.
            Must be either 3, 5, 7, 10, 15 or 20.
        depr_type (str, optional): depreciation "MACRS" or "Straight line". Defaults to 'MACRS'.
        refurb (list[float], optional): Replacement schedule as a fraction of the capital cost.
            Defaults to [0.].
        replacement_cost_percent (float | int, optional): Replacement cost as a fraction of CapEx.
            Defaults to 0.0

    """

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
    """Configuration class of default settings for ProFAST fixed costs.

    Attributes:
        escalation (float | int, optional): annual escalation of price.
            Defaults to 0.
        unit (str): unit of the cost. Defaults to `$/year`.
        usage (float, optional): Usage multiplier, likely should be set to 1.
            Defaults to 1.0.
    """

    escalation: float | int = field()
    unit: str = field(default="$/year")
    usage: float | int = field(default=1.0)

    def create_dict(self):
        return self.as_dict()


@define
class ProFASTDefaultVariableCost(BaseConfig):
    """Configuration class of default settings for ProFAST variable costs.
    The total cost is calculated as ``usage*cost``.

    Attributes:
        escalation (float | int, optional): annual escalation of price.
            Defaults to 0.
        unit (str): unit of the cost, only used for reporting. The cost should be input in
            USD/unit of commodity.
        usage (float, optional): Usage of feedstock per unit of commondity.
            Defaults to 1.0.


    """

    escalation: float | int = field()
    unit: str = field()
    usage: float | int = field(default=1.0)

    def create_dict(self):
        return self.as_dict()


@define
class ProFASTDefaultIncentive(BaseConfig):
    """Configuration class of default settings for ProFAST production-based incentives.

    Attributes:
        decay (float): rate of decay of incentive value.
            Recommended to set as -1*general inflation rate.
        sunset_years (int, optional): number of years incentive is active. Defaults to 10.
        tax_credit (bool, optional): Whether the incentive is a tax credit. Defaults to True.

    """

    decay: float | int = field()
    sunset_years: int = field(default=10, converter=int)
    tax_credit: bool = field(default=True)

    def create_dict(self):
        return self.as_dict()


class ProFastComp(om.ExplicitComponent):
    """
    This component calculates the Levelized Cost of Commodity (LCO) for a user-defined set
    of technologies and commodities, including hydrogen (LCOH), electricity (LCOE),
    ammonia (LCOA), nitrogen (LCON), and CO2 (LCOC). Only the user-defined technologies specified
    in the `tech_config` are included in the LCO stackup (or all if no specific technologies are
    defined).

    Attributes:
        tech_config (dict): Dictionary specifying the technologies to include in the
            LCO calculation. Only these technologies are considered in the stackup.
        plant_config (dict): Plant configuration parameters, including financial and
            operational settings.
        driver_config (dict): Driver configuration parameters (not directly used in calculations).
        commodity_type (str): The type of commodity for which the LCO is calculated.
            Supported values are "hydrogen", "electricity", "ammonia", "nitrogen", and "co2".

    Inputs:
        capex_adjusted_{tech} (float): Adjusted capital expenditure for each
            user-defined technology, in USD.
        opex_adjusted_{tech} (float): Adjusted operational expenditure for each
            user-defined technology, in USD/year.
        total_{commodity}_produced (float): Total annual production of the selected commodity
            (units depend on commodity type).
        {tech}_time_until_replacement (float): Time until technology is replaced, in hours
            (currently only supported if "electrolyzer" is in tech_config).
        co2_capture_kgpy (float): Total annual CO2 captured, in kg/year
            (only for commodity_type "co2").

    Outputs:
        LCOx (float): Levelized Cost of commodity (where 'x' is the uppercase first letter
            of the commodity). For example, LCOH if commodity_type is "hydrogen".
            If commodity_type is "hydrogen", "ammonia", "nitrogen", or "co2", the units are USD/kg.
            If the commodity type is "electricity", the units are USD/kWh.
        wacc_<commodity> (float): weighted average cost of capital as a fraction.
        crf_<commodity> (float): capital recovery factor as a fraction.
        irr_<commodity> (float): internal rate of return as a fraction.
        profit_index_<commodity> (float):
        investor_payback_period_<commodity> (float): time until initial investment costs are
            recovered in years.
        price_<commodity> (float): first year price of commodity in same units as `LCOx`

    Methods:
        initialize(): Declares component options.
        setup(): Defines inputs and outputs based on user configuration and validates
            required parameters.
        compute(inputs, outputs): Assembles financial parameters, adds capital and fixed cost
            items for user-defined technologies, runs the ProFAST financial model,
            and sets the appropriate LCOx output.

    Notes:
        - Only technologies specified by the user in `tech_config` are included in the LCO stackup.
        - The component supports flexible configuration for different commodities
            and technology mixes.
        - Only includes fixed annual operating costs and capital costs at the moment.
    """

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
        self.outputs_to_units = {
            "wacc": "percent",
            "crf": "percent",
            "irr": "percent",
            "profit_index": "unitless",
            "investor_payback_period": "yr",
            "price": lco_units,
        }
        for output_var, units in self.outputs_to_units.items():
            self.add_output(f"{output_var}_{self.output_txt}", val=0.0, units=units)

        if self.options["commodity_type"] == "co2":
            self.add_input("co2_capture_kgpy", val=0.0, units="kg/year")
        else:
            self.add_input(
                f"total_{self.options['commodity_type']}_produced",
                val=0.0,
                units=commodity_units,
            )

        plant_life = int(self.options["plant_config"]["plant"]["plant_life"])
        tech_config = self.tech_config = self.options["tech_config"]
        for tech in tech_config:
            self.add_input(f"capex_adjusted_{tech}", val=0.0, units="USD")
            self.add_input(f"opex_adjusted_{tech}", val=0.0, units="USD/year")
            self.add_input(f"varopex_adjusted_{tech}", val=0.0, shape=plant_life, units="USD/year")

        if "electrolyzer" in tech_config:
            self.add_input("electrolyzer_time_until_replacement", units="h")

        plant_config = self.options["plant_config"]

        finance_params = plant_config["finance_parameters"]["model_inputs"]["params"]

        fin_params = check_parameter_inputs(finance_params, plant_config)

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

        # initialize default variable cost parameters (same as feedstocks)
        variable_cost_params = plant_config["finance_parameters"]["model_inputs"].get(
            "variable_costs", {}
        )
        variable_cost_params.setdefault("escalation", self.params.inflation_rate)
        variable_cost_params.setdefault("unit", lco_units.replace("USD", "$"))
        self.variable_cost_settings = ProFASTDefaultVariableCost.from_dict(variable_cost_params)

        # incentives - unused for now
        # incentive_params = plant_config["finance_parameters"]["model_inputs"].get(
        #     "incentives", {}
        # )
        # incentive_params.setdefault("decay", -1 * self.params.inflation_rate)
        # self.incentive_params_settings = ProFASTDefaultIncentive.from_dict(incentive_params)

    def compute(self, inputs, outputs):
        mass_commodities = ["hydrogen", "ammonia", "co2", "nitrogen"]

        years_of_operation = create_years_of_operation(
            self.params.analysis_start_year,
            self.params.installation_time,
            self.params.plant_life,
        )

        # update parameters with commodity, capacity, and utilization
        profast_params = self.params.as_dict()
        profast_params["commodity"].update({"name": self.options["commodity_type"]})
        profast_params["commodity"].update(
            {"unit": "kg" if self.options["commodity_type"] in mass_commodities else "kWh"}
        )

        if self.options["commodity_type"] != "co2":
            capacity = float(inputs[f"total_{self.options['commodity_type']}_produced"][0]) / 365.0
            total_production = float(inputs[f"total_{self.options['commodity_type']}_produced"][0])
        else:
            capacity = float(inputs["co2_capture_kgpy"]) / 365.0
            total_production = float(inputs["co2_capture_kgpy"])
        if capacity == 0.0:
            raise ValueError("Capacity cannot be zero")

        profast_params["capacity"] = capacity  # TODO: update to actual daily capacity
        profast_params["long term utilization"] = 1  # TODO: update to capacity factor

        # initialize profast dictionary
        pf_dict = {"params": profast_params, "capital_items": {}, "fixed_costs": {}}

        # initialize dictionary of capital items and fixed costs
        capital_items = {}
        fixed_costs = {}
        variable_costs = {}

        # create default capital item and fixed cost entries
        capital_item_defaults = self.capital_item_settings.create_dict()
        fixed_cost_defaults = self.fixed_cost_settings.create_dict()
        variable_cost_defaults = self.variable_cost_settings.create_dict()

        # loop through technologies and create cost entries
        for tech in self.tech_config:
            # get tech-specific capital item parameters
            tech_model_inputs = self.tech_config[tech].get("model_inputs")
            if tech_model_inputs is None:
                continue  # Skip this tech if no model_inputs
            tech_capex_info = tech_model_inputs.get("financial_parameters", {}).get(
                "capital_items", {}
            )

            # add CapEx cost to tech-specific capital item entry
            tech_capex_info.update({"cost": float(inputs[f"capex_adjusted_{tech}"][0])})

            # see if any refurbishment information was input
            if "replacement_cost_percent" in tech_capex_info:
                refurb_schedule = np.zeros(self.params.plant_life)

                if "refurbishment_period_years" in tech_capex_info:
                    refurb_period = tech_capex_info["refurbishment_period_years"]
                else:
                    refurb_period = round(
                        float(inputs[f"{tech}_time_until_replacement"][0]) / (24 * 365)
                    )

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

            # get tech-specific variable cost parameters
            tech_varopex_info = (
                self.tech_config[tech]["model_inputs"]
                .get("financial_parameters", {})
                .get("variable_costs", {})
            )

            # add CapEx cost to tech-specific variable cost entry
            varom_cost_per_unit_commodity = inputs[f"varopex_adjusted_{tech}"] / total_production
            if not all(v == 0.0 for v in varom_cost_per_unit_commodity):
                varom_dict = dict(zip(years_of_operation, varom_cost_per_unit_commodity))
                tech_varopex_info.update({"cost": varom_dict})

                # update any unset variable cost parameters with the default values
                for var_cost_key, var_cost_val in variable_cost_defaults.items():
                    tech_varopex_info.setdefault(var_cost_key, var_cost_val)
                variable_costs[tech] = tech_varopex_info

        # add capital costs and fixed costs to pf_dict
        pf_dict["capital_items"] = capital_items
        pf_dict["fixed_costs"] = fixed_costs
        pf_dict["feedstocks"] = variable_costs
        # create ProFAST object

        pf = create_and_populate_profast(pf_dict)
        # simulate ProFAST
        sol, summary, price_breakdown = run_profast(pf)

        # Check whether to export profast object to .yaml file
        save_results = self.options["plant_config"]["finance_parameters"]["model_inputs"].get(
            "save_profast_results", False
        )
        save_config = self.options["plant_config"]["finance_parameters"]["model_inputs"].get(
            "save_profast_config", False
        )
        if save_results or save_config:
            pf_config_dict = convert_pf_to_dict(pf)

            output_dir = self.options["driver_config"]["general"]["folder_output"]
            fdesc = self.options["plant_config"]["finance_parameters"]["model_inputs"].get(
                "profast_output_description", "ProFastComp"
            )

            fbasename = f"{fdesc}_{self.output_txt}"

            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            if save_config:
                pf_config_dict = dict_to_yaml_formatting(pf_config_dict)
                config_fpath = Path(output_dir) / f"{fbasename}_config.yaml"
                write_yaml(pf_config_dict, config_fpath)
            if save_results:
                lco_breakdown, lco_check = make_price_breakdown(price_breakdown, pf_config_dict)
                price_breakdown_formatted = format_profast_price_breakdown_per_year(price_breakdown)
                pf_breakdown_fpath = Path(output_dir) / f"{fbasename}_profast_price_breakdown.csv"
                lco_breakdown_fpath = Path(output_dir) / f"{fbasename}_LCO_breakdown.yaml"
                price_breakdown_formatted.to_csv(pf_breakdown_fpath)
                lco_breakdown = dict_to_yaml_formatting(lco_breakdown)
                write_yaml(lco_breakdown, lco_breakdown_fpath)

        outputs[self.LCO_str] = sol["lco"]
        for output_var in self.outputs_to_units.keys():
            val = sol[output_var.replace("_", " ")]
            if isinstance(val, (np.ndarray, list, tuple)):  # only for IRR
                val = val[-1]
            outputs[f"{output_var}_{self.output_txt}"] = val
