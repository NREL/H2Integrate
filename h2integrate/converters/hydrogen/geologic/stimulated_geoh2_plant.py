import numpy as np
from attrs import field, define

from h2integrate.core.utilities import merge_shared_inputs
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
        -serp_rate:             float [1/s] - Rate constant of serpentinization reaction
        -caprock_depth:         float [m] - Depth below surface of caprock not participating in rxn
        -borehole_depth:        float [m] - Total depth of borehole (potentially including turns)
        -inj_prod_distance:     float [m] - Distance between injection and production wells
        -reaction_zone_width:   float [m] - Estimated width of rock volume participating in the rxn
        -iron_II_conc:          float [percent] - Mass % of iron (II) in the rock
        -bulk_density:          float [kg/m**3] - Bulk density of rock
        -water_temp:            float [C] - Temperature of water being injected
    """

    serp_rate: float = field()  # 1/sec
    caprock_depth: float = field()  # meters
    borehole_depth: float = field()  # meters
    inj_prod_distance: float = field()  # meters
    reaction_zone_width: float = field()  # meters
    iron_II_conc: float = field()  # wt_pct
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
        -serp_rate:             float [1/s] - Rate constant of serpentinization reaction
        -caprock_depth:         float [m] - Depth below surface of caprock not participating in rxn
        -borehole_depth:        float [m] - Total depth of borehole (potentially including turns)
        -inj_prod_distance:     float [m] - Distance between injection and production wells
        -reaction_zone_width:   float [m] - Estimated width of rock volume participating in the rxn
        -iron_II_conc:          float [percent] - Mass % of iron (II) in the rock
        -bulk_density:          float [kg/m**3] - Bulk density of rock
        -water_temp:            float [C] - Temperature of water being injected
    Outputs (in addition to those in geoh2_baseclass.GeoH2PerformanceBaseClass):
        -hydrogen_produced:     array [kg/h] - The hydrogen production profile from stimulation
                                        over 1 year (8760 hours)
    """

    def setup(self):
        self.config = StimulatedGeoH2PerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        super().setup()

        self.add_input("serp_rate", units="1/s", val=self.config.serp_rate)
        self.add_input("caprock_depth", units="m", val=self.config.caprock_depth)
        self.add_input("borehole_depth", units="m", val=self.config.borehole_depth)
        self.add_input("inj_prod_distance", units="m", val=self.config.inj_prod_distance)
        self.add_input("reaction_zone_width", units="m", val=self.config.reaction_zone_width)
        self.add_input("iron_II_conc", units="percent", val=self.config.iron_II_conc)
        self.add_input("bulk_density", units="kg/m**3", val=self.config.bulk_density)
        self.add_input("water_temp", units="C", val=self.config.water_temp)

        self.add_output("hydrogen_produced", units="kg/h", shape=(8760,))

    def compute(self, inputs, outputs):
        lifetime = int(inputs["well_lifetime"][0])

        if self.config.rock_type == "peridotite":  # TODO: sub-models for different rock types
            # Calculate serpentinization penetration rate
            grain_size = inputs["grain_size"]
            serp_rate = inputs["serp_rate"]
            pen_rate = grain_size * serp_rate

        # Model rock deposit size
        height = inputs["borehole_depth"] - inputs["caprock_depth"]
        length = inputs["inj_prod_distance"]
        width = inputs["reaction_zone_width"]
        rock_volume = height * length * width
        n_grains = rock_volume / grain_size**3
        rho = inputs["bulk_density"]
        X_Fe = inputs["iron_II_conc"]

        # Model shrinking reactive particle
        years = np.linspace(1, lifetime, lifetime)
        sec_elapsed = years * 3600 * 8760
        core_diameter = np.maximum(
            np.zeros(len(sec_elapsed)), grain_size - 2 * pen_rate * sec_elapsed
        )
        reacted_volume = n_grains * (grain_size**3 - core_diameter**3)
        reacted_mass = reacted_volume * rho * X_Fe / 100
        h2_produced = reacted_mass * M_H2 / M_Fe

        # Parse outputs
        h2_prod_avg = h2_produced[-1] / lifetime / 8760
        outputs["hydrogen_produced"] = h2_prod_avg
        outputs["hydrogen_out"] = h2_prod_avg


@define
class StimulatedGeoH2CostConfig(GeoH2CostConfig):
    """
    Cost parameters specific to the stimulated geologic hydrogen sub-models
    Values are set in the tech_config.yaml:
        technologies/geoh2/model_inputs/shared_parameters for parameters marked with *asterisks*
        technologies/geoh2/model_inputs/cost_parameters all other parameters

    Currently no parameters other than those in geoh2_baseclass.GeoH2CostConfig
    """

    cost_year: int = field(converter=int)


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

    def compute(self, inputs, outputs):
        # Calculate total capital cost per well (successful or unsuccessful)
        drill = inputs["test_drill_cost"]
        permit = inputs["permit_fees"]
        acreage = inputs["acreage"]
        rights_acre = inputs["rights_cost"]
        cap_well = drill + permit + acreage * rights_acre

        # Calculate total capital cost per SUCCESSFUL well
        completion = inputs["completion_cost"]
        success = inputs["success_chance"]
        bare_capex = cap_well / success * 100 + completion
        outputs["bare_capital_cost"] = bare_capex

        # Parse in opex
        fopex = inputs["fixed_opex"]
        vopex = inputs["variable_opex"]
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
