from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


ROOT_DIR = Path(__file__).resolve().parent


def double_exp(xy, a1, a2, b1, b2):
    x, y = xy

    return a1 * x**b1 + a2 * y**b2


fn = "Aspen_Cost_Results_simple.csv"
inputs_df = pd.read_csv(ROOT_DIR / "inputs" / fn, index_col=[0, 1], header=0)

x_data = inputs_df.loc["Mass Flow Wellhead"].values
y_data = inputs_df.loc["H2 Conc Wellhead"].values
z_data = inputs_df.loc["H2 Flow Out"].values.ravel()

xy_data = np.vstack((x_data.ravel(), y_data.ravel()))

guess = [0.001, 100, -1, 1]

popt, pcov = curve_fit(double_exp, xy_data, z_data, p0=guess)

print(inputs_df)
