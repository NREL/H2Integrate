import numpy as np
from attrs import field, define

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.tools.inflation.inflate import inflate_cpi, inflate_cepci
from h2integrate.converters.hydrogen.geologic.h2_well_subsurface_baseclass import (
    GeoH2SubsurfaceCostConfig,
    GeoH2SubsurfaceCostBaseClass,
)


@define
class GeoH2SubsurfaceCostConfig(GeoH2SubsurfaceCostConfig):
    """Configuration for subsurface well cost parameters in geologic hydrogen models.

    This configuration defines cost parameters specific to subsurface well
    components used in geologic hydrogen systems. It supports either the use of
    a built-in drilling cost curve or a manually specified constant drilling cost.

    Attributes:
        use_cost_curve (bool): Flag indicating whether to use the built-in drilling
            cost curve. If `True`, the drilling cost is computed from the cost curve.
            If `False`, a constant drilling cost must be provided.
        constant_drill_cost (float | None): Fixed drilling cost to use when
            `use_cost_curve` is `False` [USD]. Defaults to `None`.

    Raises:
        ValueError: If `use_cost_curve` is `False` and `constant_drill_cost` is not provided.
    """

    use_cost_curve: bool = field()
    constant_drill_cost: float | None = field(default=None)

    def __attrs_post_init__(self):
        # if use_cost_curve is False, constant_drill_cost must be provided
        if not self.use_cost_curve and self.constant_drill_cost is None:
            raise ValueError(
                "If 'use_cost_curve' is False, 'constant_drill_cost' must be provided."
            )


class GeoH2SubsurfaceCostModel(GeoH2SubsurfaceCostBaseClass):
    """An OpenMDAO component for modeling subsurface well costs in stimulated geologic
        hydrogen plants.

    This component estimates the capital and operating costs for subsurface well
    systems in stimulated geologic hydrogen production. Cost correlations are based on:

        - Mathur et al. (Stanford): https://doi.org/10.31223/X5599G
        - NETL Quality Guidelines: https://doi.org/10.2172/1567736

    Attributes:
        config (GeoH2SubsurfaceCostConfig): Configuration object containing cost parameters.

    Inputs:
        well_lifetime (float): Operational lifetime of the wells [years].
        target_dollar_year (int): The dollar year in which costs are modeled.
        borehole_depth (float): Depth of the wellbore [m].
        test_drill_cost (float): Capital cost of a test drill [USD].
        permit_fees (float): Cost of drilling permits [USD].
        acreage (float): Land area required for drilling [acre].
        rights_cost (float): Cost of obtaining drilling rights [USD/acre].
        success_chance (float): Probability of success for a test drill [%].
        fixed_opex (float): Fixed annual operating cost [USD/year].
        variable_opex (float): Variable operating cost per kg of H₂ produced [USD/kg].
        contracting_pct (float): Contracting costs as a percentage of bare capital cost [%].
        contingency_pct (float): Contingency costs as a percentage of bare capital cost [%].
        preprod_time (float): Duration of preproduction phase [months].
        as_spent_ratio (float): Ratio of as-spent costs to overnight costs.
        hydrogen_out (ndarray): Hydrogen production rate over time [kg/h].

    Outputs:
        bare_capital_cost (float): Unadjusted capital cost before multipliers [USD].
        CapEx (float): Total as-spent capital expenditure [USD].
        OpEx (float): Total annual operating expenditure [USD/year].
        Fixed_OpEx (float): Annual fixed operating expenditure [USD/year].
        Variable_OpEx (float): Variable operating expenditure per kg of H₂ [USD/kg].

    Raises:
        ValueError: If cost curve settings in the configuration are inconsistent.
    """

    def setup(self):
        self.config = GeoH2SubsurfaceCostConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # Get cost years
        cost_year = self.config.cost_year
        dol_year = self.config.target_dollar_year

        # Calculate total capital cost per well (successful or unsuccessful)
        drill = inflate_cepci(inputs["test_drill_cost"], cost_year, dol_year)
        permit = inflate_cpi(inputs["permit_fees"], cost_year, dol_year)
        acreage = inputs["acreage"]
        rights_acre = inflate_cpi(inputs["rights_cost"], cost_year, dol_year)
        cap_well = drill + permit + acreage * rights_acre

        # Calculate total capital cost per SUCCESSFUL well
        if self.config.use_cost_curve:
            completion = self.calc_drill_cost(inputs["borehole_depth"])
        else:
            completion = self.config.constant_drill_cost
            completion = inflate_cepci(completion, 2010, cost_year)
        completion = inflate_cepci(completion, cost_year, dol_year)
        success = inputs["success_chance"]
        bare_capex = cap_well / success * 100 + completion
        outputs["bare_capital_cost"] = bare_capex

        # Parse in opex
        fopex = inflate_cpi(inputs["fixed_opex"], cost_year, dol_year)
        vopex = inflate_cpi(inputs["variable_opex"], cost_year, dol_year)
        outputs["Fixed_OpEx"] = fopex
        outputs["Variable_OpEx"] = vopex
        production = np.sum(inputs["hydrogen_out"])
        outputs["OpEx"] = fopex + vopex * np.sum(production)

        # Apply cost multipliers to bare erected cost via NETL-PUB-22580
        contracting = inputs["contracting_pct"]
        contingency = inputs["contingency_pct"]
        preproduction = inputs["preprod_time"]
        as_spent_ratio = inputs["as_spent_ratio"]
        contracting_costs = bare_capex * contracting / 100
        epc_cost = bare_capex + contracting_costs
        contingency_costs = epc_cost * contingency / 100
        total_plant_cost = epc_cost + contingency_costs
        preprod_cost = fopex * preproduction / 12
        total_overnight_cost = total_plant_cost + preprod_cost
        tasc_toc_multiplier = as_spent_ratio  # simplifying for now - TODO model on well_lifetime
        total_as_spent_cost = total_overnight_cost * tasc_toc_multiplier
        outputs["CapEx"] = total_as_spent_cost
