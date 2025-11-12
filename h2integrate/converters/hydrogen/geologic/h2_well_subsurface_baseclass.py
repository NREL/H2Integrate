import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, CostModelBaseConfig
from h2integrate.core.validators import contains
from h2integrate.core.model_baseclasses import CostModelBaseClass
from h2integrate.tools.inflation.inflate import inflate_cepci


@define
class GeoH2SubsurfacePerformanceConfig(BaseConfig):
    """Configuration for performance parameters in natural and geologic hydrogen subsurface
        well sub-models.

    This class defines key performance parameters shared across both natural and
    stimulated subsurface geologic hydrogen models.

    Attributes:
        well_lifetime (float):
            The operational lifetime of the well in years.

        borehole_depth (float):
            Total depth of the borehole in meters, potentially including turns.

        well_diameter (str):
            The relative diameter of the well.
            Valid options: `"small"` (e.g., from `OSD3500_FY25.xlsx`) or `"large"`.

        well_geometry (str):
            The geometric structure of the well.
            Valid options: `"vertical"` or `"horizontal"`.

        rock_type (str):
            The type of rock formation being drilled to extract geologic hydrogen.
            Valid options: `"peridotite"` or `"bei_troctolite"`.

        grain_size (float):
            The grain size of the rocks used to extract hydrogen, in meters.
    """

    well_lifetime: float = field()
    borehole_depth: float = field()
    well_diameter: str = field(validator=contains(["small", "large"]))
    well_geometry: str = field(validator=contains(["vertical", "horizontal"]))
    rock_type: str = field(validator=contains(["peridotite", "bei_troctolite"]))
    grain_size: float = field()


class GeoH2SubsurfacePerformanceBaseClass(om.ExplicitComponent):
    """OpenMDAO component for modeling the performance of the well subsurface for
        geologic hydrogen.

    This component represents the performance model for geologic hydrogen production,
    which can describe either natural or stimulated hydrogen generation processes.
    All configuration inputs are sourced from a corresponding
    :class:`GeoH2PerformanceConfig` instance.

    Attributes:
        options (dict):
            OpenMDAO options dictionary that must include:
                - `plant_config` (dict): Plant-level configuration parameters.
                - `tech_config` (dict): Technology-specific configuration parameters.
                - `driver_config` (dict): Driver or simulation-level configuration parameters.
        config (GeoH2PerformanceConfig):
            Parsed configuration object containing performance model inputs.

    Inputs:
        well_lifetime (float):
            The operational lifetime of the well, in years.

        borehole_depth (float):
            The total borehole depth, in meters (may include directional sections).

        grain_size (float):
            The characteristic grain size of the rock formation, in meters.

    Outputs:
        hydrogen_out (ndarray):
            The hydrogen production rate profile over a one-year period (8760 hours),
            in kilograms per hour.
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)
        self.options.declare("driver_config", types=dict)

    def setup(self):
        # inputs
        self.add_input("well_lifetime", units="year", val=self.config.well_lifetime)
        self.add_input("borehole_depth", units="m", val=self.config.borehole_depth)
        self.add_input("grain_size", units="m", val=self.config.grain_size)

        # outputs
        self.add_output("hydrogen_out", units="kg/h", shape=(8760,))


@define
class GeoH2SubsurfaceCostConfig(CostModelBaseConfig):
    """Configuration for cost parameters in natural and geologic hydrogen well subsurface
        sub-models.

    This class defines cost parameters that are shared across both natural and
    stimulated (engineered) geologic hydrogen subsurface systems.

    Attributes:
        well_lifetime (float):
            Operational lifetime of the well, in years.

        borehole_depth (float):
            Total depth of the borehole, in meters (may include horizontal turns).

        well_diameter (str):
            Relative diameter of the well.
            Valid options: `"small"` (e.g., `OSD3500_FY25.xlsx`) or `"large"`.

        well_geometry (str):
            Structural configuration of the well.
            Valid options: `"vertical"` or `"horizontal"`.

        target_dollar_year (int):
            The dollar year used for cost normalization and comparison.

        test_drill_cost (float):
            Capital cost (CAPEX) of conducting a test drill for a potential GeoH2 well,
            in USD.

        permit_fees (float):
            Capital cost (CAPEX) associated with obtaining drilling permits, in USD.

        acreage (float):
            Land area required for drilling operations, in acres.

        rights_cost (float):
            Capital cost (CAPEX) to acquire drilling rights, in USD per acre.

        success_chance (float):
            Probability of success at a given test drilling site, expressed as a fraction.

        fixed_opex (float):
            Fixed annual operating expense (OPEX) that does not scale with hydrogen
            production, in USD/year.

        variable_opex (float):
            Variable operating expense (OPEX) that scales with hydrogen production,
            in USD/kg.

        contracting_pct (float):
            Contracting costs as a percentage of bare capital cost.

        contingency_pct (float):
            Contingency allowance as a percentage of bare capital cost.

        preprod_time (float):
            Duration of the preproduction period during which fixed OPEX is charged,
            in months.

        as_spent_ratio (float):
            Ratio of as-spent costs to overnight (instantaneous) costs, dimensionless.
    """

    well_lifetime: float = field()
    borehole_depth: float = field()
    well_diameter: str = field(validator=contains(["small", "large"]))
    well_geometry: str = field(validator=contains(["vertical", "horizontal"]))
    target_dollar_year: int = field()
    test_drill_cost: float = field()
    permit_fees: float = field()
    acreage: float = field()
    rights_cost: float = field()
    success_chance: float = field()
    fixed_opex: float = field()
    variable_opex: float = field()
    contracting_pct: float = field()
    contingency_pct: float = field()
    preprod_time: float = field()
    as_spent_ratio: float = field()


class GeoH2SubsurfaceCostBaseClass(CostModelBaseClass):
    """OpenMDAO component for modeling subsurface well costs in a geologic hydrogen plant.

    This component calculates capital and operating costs for subsurface well systems
    in a geologic hydrogen plant, applicable to both natural and stimulated hydrogen
    production modes.

    Attributes:
        config (GeoH2SubsurfaceCostConfig):
            Parsed configuration object containing subsurface cost model parameters.

    Inputs:
        well_lifetime (float):
            Operational lifetime of the wells, in years.

        target_dollar_year (int):
            The dollar year used for cost normalization and comparison.

        borehole_depth (float):
            Total borehole depth, in meters (may include directional drilling sections).

        test_drill_cost (float):
            Capital expenditure (CAPEX) cost of a test drill for a potential GeoH₂ well, in USD.

        permit_fees (float):
            CAPEX cost required to obtain drilling permits, in USD.

        acreage (float):
            Land area required for drilling operations, in acres.

        rights_cost (float):
            CAPEX cost to acquire drilling rights, in USD per acre.

        success_chance (float):
            Probability of success at a given test drilling site, expressed as a fraction or
                percent.

        fixed_opex (float):
            Fixed annual operating expense (OPEX) that does not scale with hydrogen production,
            in USD/year.

        variable_opex (float):
            Variable OPEX that scales with hydrogen production, in USD/kg.

        contracting_pct (float):
            Contracting costs as a percentage of bare capital cost.

        contingency_pct (float):
            Contingency allowance as a percentage of bare capital cost.

        preprod_time (float):
            Duration of the preproduction period during which fixed OPEX applies, in months.

        as_spent_ratio (float):
            Ratio of as-spent costs to overnight (instantaneous) costs, dimensionless.

        hydrogen_out (ndarray):
            Hydrogen production rate profile over the simulation period, in kg/h.

    Outputs:
        bare_capital_cost (float):
            Raw capital expenditure (CAPEX) without multipliers, in USD.

        CapEx (float):
            Total effective CAPEX including contracting and contingency multipliers, in USD.

        OpEx (float):
            Total operating expense (OPEX) for the system, in USD/year.

        Fixed_OpEx (float):
            Annual fixed OPEX component that does not scale with hydrogen output, in USD/year.

        Variable_OpEx (float):
            Variable OPEX per kilogram of hydrogen produced, in USD/kg.
    """

    def setup(self):
        super().setup()
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        # inputs
        self.add_input(
            # TODO: discuss how this works with "plant_life"
            "well_lifetime",
            units="year",
            val=self.config.well_lifetime,
        )
        self.add_input(
            "target_dollar_year",
            units="year",
            # TODO: discuss if we want to pull this from the `plant_config`
            val=self.config.target_dollar_year,
        )
        self.add_input("borehole_depth", units="m", val=self.config.borehole_depth)
        self.add_input("test_drill_cost", units="USD", val=self.config.test_drill_cost)
        self.add_input("permit_fees", units="USD", val=self.config.permit_fees)
        self.add_input("acreage", units="acre", val=self.config.acreage)
        self.add_input("rights_cost", units="USD/acre", val=self.config.rights_cost)
        self.add_input("success_chance", units="percent", val=self.config.success_chance)
        self.add_input("fixed_opex", units="USD/year", val=self.config.fixed_opex)
        self.add_input("variable_opex", units="USD/kg", val=self.config.variable_opex)
        self.add_input("contracting_pct", units="percent", val=self.config.contracting_pct)
        self.add_input("contingency_pct", units="percent", val=self.config.contingency_pct)
        self.add_input("preprod_time", units="month", val=self.config.preprod_time)
        self.add_input("as_spent_ratio", units=None, val=self.config.as_spent_ratio)
        self.add_input(
            "hydrogen_out",
            shape=n_timesteps,
            units="kg/h",
            desc=f"Hydrogen production rate in kg/h over {n_timesteps} hours.",
        )

        # outputs
        self.add_output("bare_capital_cost", units="USD")
        self.add_output(
            # TODO: Discuss if we should change to just "OpEx" for consistency with other models
            "Fixed_OpEx",
            units="USD/year",
        )
        self.add_output("Variable_OpEx", units="USD/kg")

    def calc_drill_cost(self, x):
        # Calculates drilling costs from pre-fit polynomial curves
        diameter = self.config.well_diameter
        geometry = self.config.well_geometry
        if geometry == "vertical":
            if diameter == "small":
                coeffs = [0.224997743, 389.2448848, 745141.2795]
            elif diameter == "large":
                coeffs = [0.224897254, 869.2069059, 703617.3915]
        elif geometry == "horizontal":
            if diameter == "small":
                coeffs = [0.247604262, 323.277597, 1058263.661]
            elif diameter == "large":
                coeffs = [0.230514884, 941.8801375, 949091.7254]
        a = coeffs[0]
        b = coeffs[1]
        c = coeffs[2]
        drill_cost = a * x**2 + b * x + c

        year = self.config.cost_year
        drill_cost = inflate_cepci(drill_cost, 2010, year)

        return drill_cost


# @define
# class GeoH2FinanceConfig(BaseConfig):
#     """
#     Finance parameters shared across both natural and geologic hydrogen sub-models
#     Values are set in the tech_config.yaml:
#         technologies/geoh2/model_inputs/shared_parameters for parameters marked with *asterisks*
#         technologies/geoh2/model_inputs/finance_parameters all other parameters

#     Parameters:
#         -*well_lifetime*:   float [years] - the length of time that the wells will operate
#         -*borehole_depth*:  float [m] - Total depth of borehole (potentially including turns)
#         -*well_diameter*:   str - The relative diameter of the well - see excel sheets for
# examples
#                                 valid options: "small" (OSD3500_FY25.xlsx), "large"
#         -*well_geometry*:   str - The shape and structure of the well being drilled
#                                 valid options: "vertical", "horizontal"
#         -eff_tax_rate:      float [percent] - effective tax rate
#         -atwacc:            float [percent] - after-tax weighted average cost of capital
#     """

#     well_lifetime: float = field()
#     borehole_depth: float = field()
#     well_diameter: str = field(validator=contains(["small", "large"]))
#     well_geometry: str = field(validator=contains(["vertical", "horizontal"]))
#     eff_tax_rate: float = field()
#     atwacc: float = field()


# class GeoH2FinanceBaseClass(om.ExplicitComponent):
#     """
#     An OpenMDAO component for modeling the financials of a geologic hydrogen plant.

#     Can be either natural or stimulated.
#     All inputs come from GeoH2FinanceConfig, except for inputs in *asterisks* which come from
#         GeoH2PerformanceBaseClass or GeoH2CostBaseClass outputs.

#     Inputs:
#         well_lifetime:     float [years] - the length of time that the wells will operate
#         eff_tax_rate:      float [percent] - effective tax rate
#         atwacc:            float [percent] - after-tax weighted average cost of capital
#         *CapEx*            float [USD] - The effective CAPEX cost with multipliers applied
#         *OpEx*             float [USD/year] - The total OPEX cost
#         *Fixed_OpEx*       float [USD/year] - The OPEX cost that does not scale with H2 production
#         *Variable_OpEx*    float [USD/kg] - The OPEX cost that scales with H2 production
#         *hydrogen*:        array [kg/h] - The hydrogen production profile over 1 year (8760 hours)
#     Outputs:
#         LCOH:              float [USD/kg] - the levelized cost of hydrogen (LCOH), per kg H2
#         LCOH_capex:        float [USD/kg] - the LCOH component attributable to CAPEX
#         LCOH_fopex:        float [USD/kg] - the LCOH component attributable to fixed OPEX
#         LCOH_vopex:        float [USD/kg] - the LCOH component attributable to variable OPEX
#     """

#     def initialize(self):
#         self.options.declare("plant_config", types=dict)
#         self.options.declare("tech_config", types=dict)
#         self.options.declare("driver_config", types=dict)

#     def setup(self):
#         n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

#         self.add_input("well_lifetime", units="year", val=self.config.well_lifetime)
#         self.add_input("eff_tax_rate", units="year", val=self.config.eff_tax_rate)
#         self.add_input("atwacc", units="year", val=self.config.atwacc)
#         self.add_input("CapEx", units="USD", val=1.0, desc="Total capital expenditure in USD.")
#         self.add_input(
#             "OpEx", units="USD/year", val=1.0, desc="Total operational expenditure in USD/year."
#         )
#         self.add_input(
#             "Fixed_OpEx",
#             units="USD/year",
#             val=1.0,
#             desc="Fixed operational expenditure in USD/year.",
#         )
#         self.add_input(
#             "Variable_OpEx",
#             units="USD/kg",
#             val=1.0,
#             desc="Variable operational expenditure in USD/kg.",
#         )
#         self.add_input(
#             "hydrogen_out",
#             shape=n_timesteps,
#             units="kg/h",
#             desc="Hydrogen production rate in kg/h.",
#         )

#         self.add_output("LCOH", units="USD/kg", desc="Levelized cost of hydrogen in USD/kg.")
#         self.add_output(
#             "LCOH_capex",
#             units="USD/kg",
#             desc="Levelized cost of hydrogen attributed to CapEx in USD/kg.",
#         )
#         self.add_output(
#             "LCOH_fopex",
#             units="USD/kg",
#             desc="Levelized cost of hydrogen attributed to fixed OpEx in USD/kg.",
#         )
#         self.add_output(
#             "LCOH_vopex",
#             units="USD/kg",
#             desc="Levelized cost of hydrogen attributed to variable OpEx in USD/kg.",
#         )
