from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class MCHStorage(BaseConfig):
    """
    Cost model representing a toluene/methylcyclohexane (TOL/MCH) hydrogen storage system.

    Costs are in 2024 USD.

    Sources:
        Breunig, H., Rosner, F., Saqline, S. et al. "Achieving gigawatt-scale green hydrogen
        production and seasonal storage at industrial locations across the U.S." *Nat Commun*
        **15**, 9049 (2024). https://doi.org/10.1038/s41467-024-53189-2

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

    #: dehydrogenation capacity [metric tonnes/day]
    Dc: float = field(init=False)

    #: hydrogenation capacity [metric tonnes/day]
    Hc: float = field(init=False)

    #: maximum storage capacity [metric tonnes]
    Ms: float = field(init=False)

    #: annual hydrogen into storage [metric tonnes]
    As: float = field(init=False)

    # overnight capital cost coefficients
    occ_coeff = (54706639.43, 147074.25, 588779.05, 20825.39, 10.31)

    #: fixed O&M cost coefficients
    foc_coeff = (3419384.73, 3542.79, 13827.02, 61.22, 0.0)

    #: variable O&M cost coefficients
    voc_coeff = (711326.78, 1698.76, 6844.86, 36.04, 376.31)

    #: cost year associated with the costs in this model
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

    def calc_cost_value(self, b0, b1, b2, b3, b4):
        """
        Calculate the value of the cost function for the given coefficients.

        Args:
            b0 (float): Coefficient representing the base cost.
            b1 (float): Coefficient for the Hc (hydrogenation capacity) term.
            b2 (float): Coefficient for the Dc (dehydrogenation capacity) term.
            b3 (float): Coefficient for the Ms (maximum storage) term.
            b4 (float): Coefficient for the As (annual hydrogen into storage) term.
        Returns:
            float: The calculated cost value based on the provided coefficients and attributes.

        """
        return b0 + (b1 * self.Hc) + (b2 * self.Dc) + (b3 * self.Ms) + b4 * self.As

    def run_costs(self):
        """Calculate the costs of TOL/MCH hydrogen storage.

        Returns:
            dict: dictionary of costs for TOL/MCH storage
        """
        cost_results = {
            "mch_capex": self.calc_cost_value(*self.occ_coeff),
            "mch_opex": self.calc_cost_value(*self.foc_coeff),
            "mch_variable_om": self.calc_cost_value(*self.voc_coeff),
            "mch_cost_year": self.cost_year,
        }
        return cost_results
