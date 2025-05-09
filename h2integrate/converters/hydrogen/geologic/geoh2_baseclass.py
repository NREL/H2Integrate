import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class GeoH2PerformanceConfig(BaseConfig):
    well_lifetime: float = field()  # years
    rock_type: str = field()
    grain_size: float = field()  # meters
    serp_rate: float = field()  # 1/sec
    caprock_depth: float = field()  # meters
    borehole_depth: float = field()  # meters
    inj_prod_distance: float = field()  # meters
    reaction_zone_width: float = field()  # meters
    site_prospectivity: float = field()  # years
    initial_wellhead_flow: float = field()  # kg/hr
    gas_reservoir_size: float = field()  # tonnes
    iron_II_conc: float = field()  # wt_pct
    bulk_density: float = field()  # kg/m^3
    water_temp: float = field()  # deg C


class GeoH2PerformanceBaseClass(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling the performance of a geologic hydrogen plant.
    yada yada yada

    Inputs:
        -yada yada yada
    Outputs:
        -yada yada yada
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("well_lifetime", units="year", val=self.config.well_lifetime)
        self.add_input("grain_size", units="m", val=self.config.grain_size)
        self.add_input("serp_rate", units="1/s", val=self.config.serp_rate)
        self.add_input("caprock_depth", units="m", val=self.config.caprock_depth)
        self.add_input("borehole_depth", units="m", val=self.config.borehole_depth)
        self.add_input("inj_prod_distance", units="m", val=self.config.inj_prod_distance)
        self.add_input("reaction_zone_width", units="m", val=self.config.reaction_zone_width)
        self.add_input("site_prospectivity", units=None, val=self.config.site_prospectivity)
        self.add_input("initial_wellhead_flow", units="kg/h", val=self.config.initial_wellhead_flow)
        self.add_input("gas_reservoir_size", units="t", val=self.config.gas_reservoir_size)
        self.add_input("iron_II_conc", units="percent", val=self.config.iron_II_conc)
        self.add_input("bulk_density", units="kg/m**3", val=self.config.bulk_density)
        self.add_input("water_temp", units="C", val=self.config.water_temp)

        self.add_output("hydrogen", units="kg/h", shape=(8760,))


@define
class GeoH2CostConfig(BaseConfig):
    well_lifetime: float = field()  # year
    cost_year: int = field()
    test_drill_cost: float = field()  # USD
    permit_fees: float = field()  # USD
    acreage: float = field()  # acre
    rights_cost: float = field()  # USD/acre
    completion_cost: float = field()  # USD
    success_chance: float = field()  # pct
    fixed_opex: float = field()  # USD/year
    variable_opex: float = field()  # USD/kg


class GeoH2CostBaseClass(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling the cost of a geologic hydrogen plant.
    yada yada yada

    Inputs:
        -yada yada yada
    Outputs:
        -yada yada yada
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
        self.add_input(
            "hydrogen",
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
    well_lifetime: float = field()  # year


class GeoH2FinanceBaseClass(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling the financial aspects of a geologic hydrogen plant.
    yada yada yada

    Inputs:
        -yada yada yada
    Outputs:
        -yada yada yada
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("well_lifetime", units="year", val=self.config.well_lifetime)
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
            "hydrogen",
            shape=8760,
            units="kg/h",
            desc="Hydrogen production rate in kg/h over 8760 hours.",
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
