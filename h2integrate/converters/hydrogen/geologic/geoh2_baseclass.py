import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig
from h2integrate.core.validators import contains


@define
class GeoH2PerformanceConfig(BaseConfig):
    """
    Performance parameters shared across both natural and geologic hydrogen sub-models.

    Values are set in the tech_config.yaml:
        technologies/geoh2/model_inputs/shared_parameters for parameters marked with *asterisks*
        technologies/geoh2/model_inputs/performance_parameters all other parameters

    Parameters:
        rock_type:         str - The type of rock being drilled into to extract geologic hydrogen
                                valid options: "peridotite"
        *well_lifetime*:   float [years] - The length of time in years that the well will operate
        grain_size:        float [m] - The grain size of the rocks used to extract hydrogen
    """

    rock_type: str = field(validator=contains(["peridotite"]))
    well_lifetime: float = field()
    grain_size: float = field()


class GeoH2PerformanceBaseClass(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling the performance of a geologic hydrogen plant.

    Can be either natural or stimulated.
    All inputs come from GeoH2PerformanceConfig.

    Inputs:
        well_lifetime: float [years] - The length of time in years that the well will operate
        grain_size:    float [m] - The grain size of the rocks used to extract hydrogen
    Outputs:
        hydrogen:      array [kg/h] - The hydrogen production profile over 1 year (8760 hours)
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("well_lifetime", units="year", val=self.config.well_lifetime)
        self.add_input("grain_size", units="m", val=self.config.grain_size)

        self.add_output("hydrogen_out", units="kg/h", shape=(8760,))


@define
class GeoH2CostConfig(BaseConfig):
    """
    Cost parameters shared across both natural and geologic hydrogen sub-models
    Values are set in the tech_config.yaml:
        technologies/geoh2/model_inputs/shared_parameters for parameters marked with *asterisks*
        technologies/geoh2/model_inputs/cost_parameters all other parameters

    Parameters:
        *well_lifetime*:   float [years] - the length of time that the wells will operate
        cost_year:         int [year] - The dollar year in which costs are modeled
        test_drill_cost:   float [USD] - The CAPEX cost of a test drill for a potential geoH2 well
        permit_fees:       float [USD] - The CAPEX cost required to obtain permits for drilling
        acreage:           float [acre] - The amount of land needed for the drilling operation
        rights_cost:       float [USD/acre] - The CAPEX cost to obtain drilling rights
        completion_cost:   float [USD] - The CAPEX cost per well required to complete a successful
                                test drill site into a full-bore production well
        success_chance:    float [pct] - The chance of success at any particular test drill site
        fixed_opex:        float [USD/year] - The OPEX cost that does not scale with H2 production
        variable_opex:     float [USD/kg] - The OPEX cost component that scales with H2 production
        contracting_pct:   float [pct] - contracting costs as % of bare capital cost
        contingency_pct:   float [pct] - contingency costs as % of bare capital cost
        preprod_time:      float [months] - time in preproduction (Fixed OPEX is charged)
        as_spent_ratio:    float [None] - ratio of as-spent costs to overnight costs
    """

    well_lifetime: float = field()
    cost_year: int = field()
    test_drill_cost: float = field()
    permit_fees: float = field()
    acreage: float = field()
    rights_cost: float = field()
    completion_cost: float = field()
    success_chance: float = field()
    fixed_opex: float = field()
    variable_opex: float = field()
    contracting_pct: float = field()
    contingency_pct: float = field()
    preprod_time: float = field()
    as_spent_ratio: float = field()


class GeoH2CostBaseClass(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling the cost of a geologic hydrogen plant.

    Can be either natural or stimulated.
    All inputs come from GeoH2CostConfig, except for inputs in *asterisks* which come from
        GeoH2PerformanceBaseClass outputs.

    Inputs:
        well_lifetime:     float [years] - the length of time that the wells will operate
        cost_year:         int [year] - The dollar year in which costs are modeled
        test_drill_cost:   float [USD] - The CAPEX cost of a test drill for a potential geoH2 well
        permit_fees:       float [USD] - The CAPEX cost required to obtain permits for drilling
        acreage:           float [acre] - The amount of land needed for the drilling operation
        rights_cost:       float [USD/acre] - The CAPEX cost to obtain drilling rights
        completion_cost:   float [USD] - The CAPEX cost per well required to complete a successful
                                test drill site into a full-bore production well
        success_chance:    float [pct] - The chance of success at any particular test drill site
        fixed_opex:        float [USD/year] - The OPEX cost that does not scale with H2 production
        variable_opex:     float [USD/kg] - The OPEX cost that scales with H2 production
        contracting_pct:   float [pct] - contracting costs as % of bare capital cost
        contingency_pct:   float [pct] - contingency costs as % of bare capital cost
        preprod_time:      float [months] - time in preproduction (Fixed OPEX is charged)
        as_spent_ratio:    float [None] - ratio of as-spent costs to overnight costs
        *hydrogen*:        array [kg/h] - The hydrogen production profile over 1 year (8760 hours)
    Outputs:
        bare_capital_cost  float [USD] - The raw CAPEX cost without any multipliers applied
        CapEx              float [USD] - The effective CAPEX cost with multipliers applied
        OpEx               float [USD/year] - The total OPEX cost
        Fixed_OpEx         float [USD/year] - The OPEX cost that does not scale with H2 production
        Variable_OpEx      float [USD/kg] - The OPEX cost that scales with H2 production
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("well_lifetime", units="year", val=self.config.well_lifetime)
        self.add_input("test_drill_cost", units="USD", val=self.config.test_drill_cost)
        self.add_input("permit_fees", units="USD", val=self.config.permit_fees)
        self.add_input("acreage", units="acre", val=self.config.acreage)
        self.add_input("rights_cost", units="USD/acre", val=self.config.rights_cost)
        self.add_input("completion_cost", units="USD", val=self.config.completion_cost)
        self.add_input("success_chance", units="percent", val=self.config.success_chance)
        self.add_input("fixed_opex", units="USD/year", val=self.config.fixed_opex)
        self.add_input("variable_opex", units="USD/kg", val=self.config.variable_opex)
        self.add_input("contracting_pct", units="percent", val=self.config.contracting_pct)
        self.add_input("contingency_pct", units="percent", val=self.config.contingency_pct)
        self.add_input("preprod_time", units="month", val=self.config.preprod_time)
        self.add_input("as_spent_ratio", units=None, val=self.config.as_spent_ratio)
        self.add_input(
            "hydrogen_out",
            shape=8760,
            units="kg/h",
            desc="Hydrogen production rate in kg/h over 8760 hours.",
        )

        self.add_output("bare_capital_cost", units="USD")
        self.add_output("CapEx", units="USD")
        self.add_output("OpEx", units="USD/year")
        self.add_output("Fixed_OpEx", units="USD/year")
        self.add_output("Variable_OpEx", units="USD/kg")


@define
class GeoH2FinanceConfig(BaseConfig):
    """
    Finance parameters shared across both natural and geologic hydrogen sub-models
    Values are set in the tech_config.yaml:
        technologies/geoh2/model_inputs/shared_parameters for parameters marked with *asterisks*
        technologies/geoh2/model_inputs/finance_parameters all other parameters

    Parameters:
        *well_lifetime*:   float [years] - the length of time that the wells will operate
        eff_tax_rate:      float [percent] - effective tax rate
        atwacc:            float [percent] - after-tax weighted average cost of capital
    """

    well_lifetime: float = field()
    eff_tax_rate: float = field()
    atwacc: float = field()


class GeoH2FinanceBaseClass(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling the financials of a geologic hydrogen plant.

    Can be either natural or stimulated.
    All inputs come from GeoH2FinanceConfig, except for inputs in *asterisks* which come from
        GeoH2PerformanceBaseClass or GeoH2CostBaseClass outputs.

    Inputs:
        well_lifetime:     float [years] - the length of time that the wells will operate
        eff_tax_rate:      float [percent] - effective tax rate
        atwacc:            float [percent] - after-tax weighted average cost of capital
        *CapEx*            float [USD] - The effective CAPEX cost with multipliers applied
        *OpEx*             float [USD/year] - The total OPEX cost
        *Fixed_OpEx*       float [USD/year] - The OPEX cost that does not scale with H2 production
        *Variable_OpEx*    float [USD/kg] - The OPEX cost that scales with H2 production
        *hydrogen*:        array [kg/h] - The hydrogen production profile over 1 year (8760 hours)
    Outputs:
        LCOH:              float [USD/kg] - the levelized cost of hydrogen (LCOH), per kg H2
        LCOH_capex:        float [USD/kg] - the LCOH component attributable to CAPEX
        LCOH_fopex:        float [USD/kg] - the LCOH component attributable to fixed OPEX
        LCOH_vopex:        float [USD/kg] - the LCOH component attributable to variable OPEX
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("well_lifetime", units="year", val=self.config.well_lifetime)
        self.add_input("eff_tax_rate", units="year", val=self.config.eff_tax_rate)
        self.add_input("atwacc", units="year", val=self.config.atwacc)
        self.add_input("CapEx", units="USD", val=1.0, desc="Total capital expenditure in USD.")
        self.add_input(
            "OpEx", units="USD/year", val=1.0, desc="Total operational expenditure in USD/year."
        )
        self.add_input(
            "Fixed_OpEx",
            units="USD/year",
            val=1.0,
            desc="Fixed operational expenditure in USD/year.",
        )
        self.add_input(
            "Variable_OpEx",
            units="USD/kg",
            val=1.0,
            desc="Variable operational expenditure in USD/kg.",
        )
        self.add_input(
            "hydrogen_out",
            shape=8760,
            units="kg/h",
            desc="Hydrogen production rate in kg/h.",
        )

        self.add_output("LCOH", units="USD/kg", desc="Levelized cost of hydrogen in USD/kg.")
        self.add_output(
            "LCOH_capex",
            units="USD/kg",
            desc="Levelized cost of hydrogen attributed to CapEx in USD/kg.",
        )
        self.add_output(
            "LCOH_fopex",
            units="USD/kg",
            desc="Levelized cost of hydrogen attributed to fixed OpEx in USD/kg.",
        )
        self.add_output(
            "LCOH_vopex",
            units="USD/kg",
            desc="Levelized cost of hydrogen attributed to variable OpEx in USD/kg.",
        )
