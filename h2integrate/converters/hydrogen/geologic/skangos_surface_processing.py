from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


ROOT_DIR = Path(__file__).resolve().parent


def polynom(xy, a1, a2, a3, a4):
    x, y = xy

    return a1 * x**2 + a2 * x * y + a3 * y**2 + a4


def double_exp(xy, a1, a2, a3, a4):
    x, y = xy

    return a1 * x**a2 + a3 * y**a4


def double_log(xy, a1, a3):
    x, y = xy

    return a1 * np.log(x) + a3 * np.log(y)


fn = "Aspen_Cost_Results_simple.csv"
inputs_df = pd.read_csv(ROOT_DIR / "inputs" / fn, index_col=[0, 1], header=0)

x_data = inputs_df.loc["Mass Flow Wellhead"].values.ravel()
y_data = inputs_df.loc["H2 Conc Wellhead"].values.ravel()
z_data = inputs_df.loc["H2 Flow Out"].values.ravel() / x_data

xy_data = np.vstack((x_data, y_data))

# guess = [0.001, 1, 100, -1]

popt, pcov = curve_fit(double_exp, xy_data, z_data)  # , p0=guess)

x_axis_pts = np.arange(1000, 100000, 1000)
y_axis_pts = np.arange(0.01, 1, 0.01)

x_grid, y_grid = np.meshgrid(x_axis_pts, y_axis_pts)
z_surf = double_exp((x_grid, y_grid), *popt)

# levels = np.arange(0,.3,0.01)
cplot = plt.contourf(x_axis_pts, y_axis_pts, z_surf * x_grid, cmap="plasma", levels=256)

cmap_min = np.min(cplot.levels)
cmap_max = np.max(cplot.levels)
color_N = cplot.cmap.N
for point_ind, point in enumerate(z_data * x_data):
    point_color_frac = (point - cmap_min) / (cmap_max - cmap_min)
    plt.plot(
        x_data[point_ind], y_data[point_ind], "o", zorder=1, color=cplot.cmap(point_color_frac)[:3]
    )
plt.colorbar()
plt.show()
