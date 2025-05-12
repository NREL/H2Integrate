from attrs import field, define

from h2integrate.core.utilities import BaseConfig


def calc_value(sizes, b0, b1, b2, b3, b4):
    Hc, Dc, Ms, As = sizes
    cost = b0 + (b1 * Hc) + (b2 * Dc) + (b3 * Ms) + b4 * As
    return cost


@define
class MCHStorage(BaseConfig):
    """

    Sources:
        - "Achieving gigawatt-scale green hydrogen production and
        seasonal storage at industrial locations across the U.S" which is
        [linked here](https://www.nature.com/articles/s41467-024-53189-2)

    Args:
        max_H2_production_kg_pr_hr (float): Maximum amount of hydrogen that may be
            used to fill storage in kg/hr.
        hydrogen_storage_capacity_kg (float): Hydrogen storage capacity in kilograms.
        hydrogen_demand_kg_pr_hr (float):  Hydrogen demand in kg/hr.
        annual_hydrogen_stored_kg_pr_yr (float): Sum of hydrogen used to fill storage
            in kg/year.
    """

    max_H2_production_kg_pr_hr: float
    hydrogen_storage_capacity_kg: float
    hydrogen_demand_kg_pr_hr: float
    annual_hydrogen_stored_kg_pr_yr: float

    # dehydrogenation capacity [metric tonnes/day]
    Dc: float = field(init=False)

    # hydrogenation capacity [metric tonnes/day]
    Hc: float = field(init=False)

    # maximum storage capacity [metric tonnes]
    Ms: float = field(init=False)

    # annual hydrogen into storage [metric tonnes]
    As: float = field(init=False)

    # overnight capital cost coefficients
    occ_coeff = (54706639.43, 147074.25, 588779.05, 20825.39, 10.31)
    # fixed O&M cost coefficients
    foc_coeff = (3419384.73, 3542.79, 13827.02, 61.22, 0.0)
    # variable O&M cost coefficients
    voc_coeff = (711326.78, 1698.76, 6844.86, 36.04, 376.31)

    # cost year associated with the costs in this model
    cost_year = 2024

    def __attrs_post_init__(self):
        # Equation (3): DC = P_avg
        self.Dc = self.hydrogen_demand_kg_pr_hr * 24 / 1e3

        # Equation (2): HC = P_nameplate - P_avg
        P_nameplate = self.max_H2_production_kg_pr_hr * 24 / 1e3
        self.Hc = P_nameplate - self.Dc

        # Equation (1): AS = sum(curtailed_h2)
        self.As = self.annual_hydrogen_stored_kg_pr_yr / 1e3

        # Defined in paragraph between Equation (2) and (3)
        self.Ms = self.hydrogen_storage_capacity_kg / 1e3

    def calc_capex(self):
        capex = calc_value((self.Hc, self.Dc, self.Ms, self.As), *self.occ_coeff)
        return capex

    def calc_variable_om(self):
        vom = calc_value((self.Hc, self.Dc, self.Ms, self.As), *self.voc_coeff)
        return vom

    def calc_fixed_om(self):
        fixed_om = calc_value((self.Hc, self.Dc, self.Ms, self.As), *self.foc_coeff)
        return fixed_om

    def run_costs(self):
        capex = self.calc_capex()
        var_om = self.calc_variable_om()
        fixed_om = self.calc_fixed_om()

        cost_results = {
            "mch_capex": capex,
            "mch_opex": fixed_om,
            "mch_variable_om": var_om,
            "mch_cost_year": self.cost_year,
        }
        return cost_results
