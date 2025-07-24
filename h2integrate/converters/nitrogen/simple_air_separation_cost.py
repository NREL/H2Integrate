import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains


def make_cost_unit_multiplier(unit_str):
    if unit_str == "none":
        return 0.0, "power"

    power_based_value = unit_str == "mw" or unit_str == "kw"
    # mass_based_value = unit_str != 'mw' and unit_str != 'kw'
    k = 1.0

    if power_based_value:
        if unit_str == "mw":
            k = 1 / 1e3  # use as mupltiplier to convert from MW -> kW
        return k, "power"

    # convert from units to kg/hour
    if "day" in unit_str:  # convert from daily units to hourly units
        cpx_k = 24
    if "tonne" in unit_str:
        cpx_k *= 1 / 1e3
    return k, "mass"


@define
class SimpleASUCostConfig(BaseConfig):
    capex_usd_per_unit: float = field()

    capex_unit: str = field(
        validator=contains(["kg/hour", "kw", "mw", "tonne/hour", "kg/day", "tonne/day"]),
        converter=(str.strip, str.lower),
    )

    opex_usd_per_unit_per_year: float = field(default=0.0)
    opex_unit: str = field(
        default="none",
        validator=contains(["kg/hour", "kw", "mw", "tonne/hour", "kg/day", "tonne/day", "none"]),
        converter=(str.strip, str.lower),
    )

    def __attrs_post_init__(self):
        if self.opex_usd_per_unit_per_year > 0 and self.opex_unit == "none":
            msg = (
                "User provided opex value but did not specify units. "
                "Please specify opex_unit as one of the following: "
                "kg/hour, kw, MW, tonne/hour, kg/day, or tonne/day"
            )
            raise ValueError(msg)


class SimpleASUCostModel(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)
        self.options.declare("driver_config", types=dict)

    def setup(self):
        self.config = SimpleASUCostConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

        self.add_input("ASU_capacity_kW", val=0.0, units="kW")
        self.add_input("rated_N2_kg_pr_hr", val=0.0, units="kg/h")

        self.add_output("CapEx", val=0.0, units="USD")
        self.add_output("OpEx", val=0.0, units="USD/year")

    def compute(self, inputs, outputs):
        # Get config values
        capex_k, capex_based_unit = make_cost_unit_multiplier(self.config.capex_unit)
        unit_capex = self.config.capex_usd_per_unit * capex_k
        if capex_based_unit == "power":
            capex_usd = unit_capex * inputs["ASU_capacity_kW"]
        else:
            capex_usd = unit_capex * inputs["rated_N2_kg_pr_hr"]

        opex_k, opex_based_unit = make_cost_unit_multiplier(self.config.opex_unit)
        unit_opex = self.config.opex_usd_per_unit_per_year * opex_k
        if opex_based_unit == "power":
            opex_usd_per_year = unit_opex * inputs["ASU_capacity_kW"]
        else:
            opex_usd_per_year = unit_opex * inputs["rated_N2_kg_pr_hr"]

        outputs["CapEx"] = capex_usd
        outputs["OpEx"] = opex_usd_per_year
