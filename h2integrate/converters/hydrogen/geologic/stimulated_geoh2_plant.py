import numpy as np
from attrs import field, define

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.tools.inflation.inflate import inflate_cpi, inflate_cepci
from h2integrate.converters.hydrogen.geologic.geoh2_baseclass import (
    GeoH2CostConfig,
    GeoH2CostBaseClass,
    GeoH2FinanceConfig,
    GeoH2FinanceBaseClass,
    GeoH2PerformanceConfig,
    GeoH2PerformanceBaseClass,
)


# Globals - molecular weights
M_Fe = 55.8  # kg/kmol
M_H2 = 1.00  # kg/kmol


@define
class StimulatedGeoH2PerformanceConfig(GeoH2PerformanceConfig):
    """
    Performance parameters specific to the stimulated geologic hydrogen sub-models
    Values are set in the tech_config.yaml:
        technologies/geoh2/model_inputs/shared_parameters for parameters marked with *asterisks*
        technologies/geoh2/model_inputs/performance_parameters all other parameters

    Parameters (in addition to those in geoh2_baseclass.GeoH2PerformanceConfig):
        -olivine_phase_vol:     float [percent] - The volume percent of olivine in the formation
        -olivine_fe_ii_conc:    float [percent] - The mass percent of iron (II) in the olivine
        -depth_to_formation:    float [m] - Depth below surface of caprock not participating in rxn
        -inj_prod_distance:     float [m] - Distance between injection and production wells
        -reaction_zone_width:   float [m] - Estimated width of rock volume participating in the rxn
        -bulk_density:          float [kg/m**3] - Bulk density of rock
        -water_temp:            float [C] - Temperature of water being injected
    """

    olivine_phase_vol: float = field()  # vol pct
    olivine_fe_ii_conc: float = field()  # wt pct
    depth_to_formation: float = field()  # meters
    inj_prod_distance: float = field()  # meters
    reaction_zone_width: float = field()  # meters
    bulk_density: float = field()  # kg/m^3
    water_temp: float = field()  # deg C


class StimulatedGeoH2PerformanceModel(GeoH2PerformanceBaseClass):
    """
    An OpenMDAO component for modeling the performance of a stimulated geologic hydrogen plant.
    Based on the work of:
        - Mathur et al. (Stanford): https://eartharxiv.org/repository/view/8321/
        - Templeton et al. (UC Boulder): https://doi.org/10.3389/fgeoc.2024.1366268

    All inputs come from StimulatedGeoH2PerformanceConfig

    Inputs (in addition to those in geoh2_baseclass.GeoH2PerformanceBaseClass):
        -olivine_phase_vol:     float [percent] - The volume percent of olivine in the formation
        -olivine_fe_ii_conc:    float [percent] - The mass percent of iron (II) in the olivine
        -depth_to_formation:    float [m] - Depth below surface of caprock not participating in rxn
        -inj_prod_distance:     float [m] - Distance between injection and production wells
        -reaction_zone_width:   float [m] - Estimated width of rock volume participating in the rxn
        -bulk_density:          float [kg/m**3] - Bulk density of rock
        -water_temp:            float [C] - Temperature of water being injected
    Outputs (in addition to those in geoh2_baseclass.GeoH2PerformanceBaseClass):
        -hydrogen_out_stim:     array [kg/h] - The hydrogen production profile from stimulation
                                        over 1 year (8760 hours)
    """

    def setup(self):
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        self.config = StimulatedGeoH2PerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        super().setup()

        self.add_input("olivine_phase_vol", units="percent", val=self.config.olivine_phase_vol)
        self.add_input("olivine_fe_ii_conc", units="percent", val=self.config.olivine_fe_ii_conc)
        self.add_input("depth_to_formation", units="m", val=self.config.depth_to_formation)
        self.add_input("inj_prod_distance", units="m", val=self.config.inj_prod_distance)
        self.add_input("reaction_zone_width", units="m", val=self.config.reaction_zone_width)
        self.add_input("bulk_density", units="kg/m**3", val=self.config.bulk_density)
        self.add_input("water_temp", units="C", val=self.config.water_temp)

        self.add_output("hydrogen_out_stim", units="kg/h", shape=n_timesteps)

    def compute(self, inputs, outputs):
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        lifetime = int(inputs["well_lifetime"][0])

        # Calculate serpentinization penetration rate
        grain_size = inputs["grain_size"]
        lin_coeff = 1.00e-6
        exp_coeff = -0.000209
        orig_size = 0.0000685  # meters
        temp = inputs["water_temp"]
        serp_rate = (
            lin_coeff
            * np.exp(exp_coeff * (temp - 260) ** 2)
            * 10 ** np.log10(orig_size / grain_size)
        )
        pen_rate = grain_size * serp_rate

        # Model rock deposit size
        height = inputs["borehole_depth"] - inputs["depth_to_formation"]
        length = inputs["inj_prod_distance"]
        width = inputs["reaction_zone_width"]
        rock_volume = height * length * width
        v_olivine = inputs["olivine_phase_vol"] / 100
        n_grains = rock_volume / grain_size**3 * v_olivine
        rho = inputs["bulk_density"]
        X_Fe = inputs["olivine_fe_ii_conc"] / 100

        # Model shrinking reactive particle
        years = np.linspace(1, lifetime, lifetime)
        sec_elapsed = years * 3600 * n_timesteps
        core_diameter = np.maximum(
            np.zeros(len(sec_elapsed)), grain_size - 2 * pen_rate * sec_elapsed
        )
        reacted_volume = n_grains * (grain_size**3 - core_diameter**3)
        reacted_mass = reacted_volume * rho * X_Fe
        h2_produced = reacted_mass * M_H2 / M_Fe

        # Parse outputs
        h2_prod_avg = h2_produced[-1] / lifetime / n_timesteps
        outputs["hydrogen_out_stim"] = h2_prod_avg
        outputs["hydrogen_out"] = h2_prod_avg


@define
class StimulatedGeoH2CostConfig(GeoH2CostConfig):
    """
    Cost parameters specific to the stimulated geologic hydrogen sub-models
    Values are set in the tech_config.yaml:
        technologies/geoh2/model_inputs/shared_parameters for parameters marked with *asterisks*
        technologies/geoh2/model_inputs/cost_parameters all other parameters

    Args:
        use_cost_curve (bool): Whether to use the built in drilling cost curve or a manual value
        constant_drill_cost (float): If use_cost_curve is False, the constant cost of drilling
    """

    use_cost_curve: bool = field()
    constant_drill_cost: float = field(default=1000000)


class StimulatedGeoH2CostModel(GeoH2CostBaseClass):
    """
    An OpenMDAO component for modeling the cost of a stimulated geologic hydrogen plant
    Based on the work of:
        - Mathur et al. (Stanford): https://eartharxiv.org/repository/view/8321/
        - NETL Quality Guidelines: https://doi.org/10.2172/1567736

    All inputs come from StimulatedGeoH2CostConfig, except for inputs in *asterisks* which come
        from StimulatedGeoH2PerformanceModel

    Currently no inputs/outputs other than those in geoh2_baseclass.GeoH2CostBaseClass
    """

    def setup(self):
        self.config = StimulatedGeoH2CostConfig.from_dict(
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


class StimulatedGeoH2FinanceModel(GeoH2FinanceBaseClass):
    """
    An OpenMDAO component for modeling the financing of a stimulated geologic hydrogen plant
    Based on the work of:
        - Mathur et al. (Stanford): https://eartharxiv.org/repository/view/8321/
        - NETL Quality Guidelines: https://doi.org/10.2172/1567736

    All inputs come from StimulatedGeoH2FinanceConfig, except for inputs in *asterisks* which come
        from StimulatedGeoH2PerformanceModel or StimulatedGeoH2CostModel outputs

    Currently no inputs/outputs other than those in geoh2_baseclass.GeoH2FinanceBaseClass
    """

    def setup(self):
        self.config = GeoH2FinanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "finance")
        )
        super().setup()

    def compute(self, inputs, outputs):
        # Calculate fixed charge rate
        lifetime = int(inputs["well_lifetime"][0])
        etr = inputs["eff_tax_rate"] / 100
        atwacc = inputs["atwacc"] / 100
        dep_n = 1 / lifetime  # simplifying the IRS tax depreciation tables to avoid lookup
        crf = (
            atwacc * (1 + atwacc) ** lifetime / ((1 + atwacc) ** lifetime - 1)
        )  # capital recovery factor
        dep = crf * np.sum(dep_n / np.power(1 + atwacc, np.linspace(1, lifetime, lifetime)))
        fcr = crf / (1 - etr) - etr * dep / (1 - etr)

        # Calculate levelized cost of geoH2
        capex = inputs["CapEx"]
        fopex = inputs["Fixed_OpEx"]
        vopex = inputs["Variable_OpEx"]
        production = np.sum(inputs["hydrogen_out"])
        lcoh = (capex * fcr + fopex) / production + vopex
        outputs["LCOH"] = lcoh
        outputs["LCOH_capex"] = (capex * fcr) / production
        outputs["LCOH_fopex"] = fopex / production
        outputs["LCOH_vopex"] = vopex
