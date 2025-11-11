import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.core.validators import contains
from h2integrate.core.model_baseclasses import CostModelBaseClass


# Physical constants
f = 96485.3321  # Faraday constant: Electric charge per mole of electrons (Faraday constant), C/mol
M = 0.055845  # Electrolysis product molar mass (kg/mol)

# Default coefficents for Stinn capex model
a1n = 51010
a1d = -3.82e-03
a1t = -631
a2n = 5634000
a2d = -7.1e-03
a2t = 349
a3n = 750000
e1 = 0.8
e2 = 0.9
e3 = 0.15
e4 = 0.5


def stinn_capex_calc(
    a1n, a1d, a1t, a2n, a2d, a2t, a3n, e1, e2, e3, e4, T, P, p, z, F, j, A, e, M, Q, V, N
):
    """
    Equation (7) from Stinn: doi.org/10.1149.2/2.F06202IF
    default values for coefficients defined as globals
    """
    # Pre-costs calculation
    a1 = a1n / (1 + np.exp(a1d * (T - a1t)))
    a2 = a2n / (1 + np.exp(a2d * (T - a2t)))
    a3 = a3n * Q

    pre_costs = a1 * P**e1

    # Electrolysis and product handling contribution to total cost
    electrolysis_product_handling = a2 * ((p * z * F) / (j * A * e * M)) ** e2

    # Power rectifying contribution
    power_rectifying_contribution = a3 * V**e3 * N**e4

    return pre_costs, electrolysis_product_handling, power_rectifying_contribution, a1, a2, a3


@define
class HumbertStinnEwinCostConfig(CostModelBaseClass):
    electrolysis_type: str = field(
        kw_only=True, converter=(str.lower, str.strip), validator=contains(["ahe", "mse", "moe"])
    )  # product selection


class HumbertStinnEwinCostComponent(om.ExplicitComponent):
    """
    Humbert: doi.org/10.1007/s40831-024-00878-3
    Stinn: doi.org/10.1149.2/2.F06202IF
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        self.config = HumbertStinnEwinCostConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=False,
        )

        ewin_type = self.config.electrolysis_type

        # Lookup specific inputs for electrowinning types from Humbert SI except where noted
        if ewin_type == "ahe":
            # AHE - Capex
            T = 100  # Electrolysis temperature (°C)
            z = 2  # Moles of electrons per mole of iron product
            V = 1.7  # Cell operating voltage (V)
            j = 1000  # Current density (A/m²)
            A = 250  # Electrode area per cell (m²)
            e = 0.66  # Current efficiency (dimensionless)
            N = 12  # Number of rectifier lines
            # E_spec taken from Humbert Table 10 - average of Low and High estimates
            E_spec = (1.869 + 2.72) / 2  # Specific energy of electrolysis (kWh/kg-Fe)

            # AHE - Opex
            labor = (0.44 + 1.54) / 2  # Labor rate (op.-hr/tonne)
            NaOH_ratio = 25130.2 * 0.1 / 2e6  # Ratio of NaOH consumption to annual iron production
            CaCl2_ratio = 0  # Ratio of CaCl2 consumption to annual iron production
            limestone_ratio = 0  # Ratio of limestone consumption to annual iron production
            anode_ratio = 0  # Ratio of annode mass to annual iron production
            # Anode replacement interval not considered by Humbert, 3 years assumed here
            anode_replace_year = 3  # Replacement interval of anodes, years

        elif ewin_type == "mse":
            # MSE - Capex
            T = 900  # Temperature (deg C)
            z = 3  # Moles of electrons per mole of iron product
            V = 3  # Cell operating voltage (V)
            j = 300  # Current density (A/m²)
            A = 250  # Electrode area per cell (m²)
            e = 0.66  # Current efficiency (dimensionless)
            N = 8  # Number of rectifier lines
            # E_spec taken from Humbert Table 10 - average of Low and High estimates
            E_spec = (1.81 + 2.08) / 2  # Specific energy of electrolysis (kWh/kg-Fe)

            # MSE - Opex
            labor = (0.44 + 1.54) / 2  # Labor rate (op.-hr/tonne)
            NaOH_ratio = 0  # Ratio of NaOH consumption to annual iron production
            CaCl2_ratio = 23138 * 0.1 / 2e6  # Ratio of CaCl2 consumption to annual iron production
            limestone_ratio = 0  # Ratio of limestone consumption to annual iron production
            anode_ratio = 1589.3 / 2e6  # Ratio of annode mass to annual iron production
            # Anode replacement interval not considered by Humbert, 3 years assumed here
            anode_replace_year = 3  # Replacement interval of anodes, years

        elif ewin_type == "moe":
            # MOE - Capex
            T = 1600  # Temperature (deg C)
            z = 2  # Moles of electrons per mole of iron product
            V = 4.22  # Cell operating voltage (V)
            j = 10000  # Current density (A/m²)
            A = 30  # Electrode area per cell (m²)
            e = 0.95  # Current efficiency (dimensionless)
            N = 6  # Number of rectifier lines
            # E_spec taken from Humbert Table 10 - average of Low and High estimates
            E_spec = (2.89 + 4.45) / 2  # Specific energy of electrolysis (kWh/kg-Fe)

            # AHE - Opex
            labor = 0.358  # Labor rate (op.-hr/tonne)
            NaOH_ratio = 0  # Ratio of NaOH consumption to annual iron production
            CaCl2_ratio = 0  # Ratio of CaCl2 consumption to annual iron production
            limestone_ratio = 0  # Ratio of limestone consumption to annual iron production
            anode_ratio = 8365.6 / 2e6  # Ratio of annode mass to annual iron production
            # Anode replacement interval not considered by Humbert, 3 years assumed here
            anode_replace_year = 3  # Replacement interval of anodes, years

        self.add_input("electrolysis_temp", val=T, units="C")
        self.add_input("output_capacity", val=0.0, units="Mg/year")  # Mg = tonnes

        # Temporary to make ruff happy
        self.inputs = [
            T,
            z,
            j,
            A,
            e,
            M,
            E_spec,
            V,
            N,
            labor,
            NaOH_ratio,
            CaCl2_ratio,
            limestone_ratio,
            anode_ratio,
            anode_replace_year,
        ]

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        stinn_capex_calc(
            a1n,
            a1d,
            a1t,
            a2n,
            a2d,
            a2t,
            a3n,
            e1,
            e2,
            e3,
            e4,  # T, P, p, z, F, j, A, e, M, Q, V, N
        )
