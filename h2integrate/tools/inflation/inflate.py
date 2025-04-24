"""
Inflates with cpi or cepci
"""

from pathlib import Path

import numpy as np
import pandas as pd


def inflate_cpi(costs, in_year, out_year):
    CD = Path(__file__).parent.resolve()
    cpi_df = pd.read_csv(CD / "cpi.csv", index_col=0)
    ratio = cpi_df.loc[out_year, "CPI"] / cpi_df.loc[in_year, "CPI"]
    inflated_costs = np.multiply(costs, ratio)

    return inflated_costs


def inflate_cepci(costs, in_year, out_year):
    CD = Path(__file__).parent.resolve()
    cpi_df = pd.read_csv(CD / "cepci.csv", index_col=0)
    ratio = cpi_df.loc[out_year, "CEPCI"] / cpi_df.loc[in_year, "CEPCI"]
    inflated_costs = np.multiply(costs, ratio)

    return inflated_costs
