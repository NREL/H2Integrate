from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


ROOT_DIR = Path(__file__).resolve().parent


def polynom(xy, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15):
    x, y = xy

    z = (
        a1
        + a2 * x
        + a3 * y
        + a4 * x**2
        + a5 * x * y
        + a6 * y**2
        + a7 * x**3
        + a8 * x**2 * y
        + a9 * x * y**2
        + a10 * y**3
        + a11 * x**4
        + a12 * x**3 * y
        + a13 * x**2 * y**2
        + a14 * x * y**3
        + a15 * y**4
    )

    return z


def double_exp(xy, a1, a2, a3, a4):
    x, y = xy

    return a1 * x**a2 + a3 * y**a4


def double_log(xy, a1, a2, a3, a4, a5, a6):
    x, y = xy

    return (
        a1
        + a2 * np.log(x)
        + a3 * np.log(y)
        + a4 * np.log(x) ** 2
        + a5 * np.log(x) * np.log(y)
        + a6 * np.log(y) ** 2
    )


fn = "cases.csv"
inputs_df = pd.read_csv(ROOT_DIR / "ex_04_out" / fn, index_col=0, header=0)

x_data = inputs_df.loc[:, "geoh2_well_subsurface.site_prospectivity (unitless)"].values.ravel()
y_data = inputs_df.loc[:, "geoh2_well_subsurface.initial_wellhead_flow (kg/h)"].values.ravel()
z_data = np.log(inputs_df.loc[:, "finance_subgroup_h2.LCOH (USD/kg)"].values.ravel())
# z_data = np.log(inputs_df.loc[:, "finance_subgroup_h2.total_capex_adjusted (USD)"].values.ravel())

xy_data = np.vstack((x_data, y_data))

# guess = [1, 1, -1, 1, -1]
popt, pcov = curve_fit(double_log, xy_data, z_data)  # , p0=guess)
# popt, pcov = curve_fit(polynom, xy_data, z_data)#, p0=guess)

y_axis_pts = np.exp(np.linspace(np.log(1000), np.log(100000), 100))
x_axis_pts = np.linspace(0.1, 1, 100)

x_grid, y_grid = np.meshgrid(x_axis_pts, y_axis_pts)
z_surf = double_log((x_grid, y_grid), *popt)
# z_surf = polynom((x_grid, y_grid), *popt)

levels = np.arange(0, 10, 0.1)
cplot = plt.contourf(x_axis_pts * 100, y_axis_pts, np.exp(z_surf), cmap="turbo", levels=levels)

cmap_min = np.min(cplot.levels)
cmap_max = np.max(cplot.levels)
color_N = cplot.cmap.N
for point_ind, point in enumerate(np.exp(z_data)):
    point_color_frac = (point - cmap_min) / (cmap_max - cmap_min)
    plt.plot(
        x_data[point_ind] * 100,
        y_data[point_ind],
        "o",
        zorder=1,
        color=cplot.cmap(point_color_frac)[:3],
    )

cbar = plt.colorbar()
cbar_label = cbar.set_label("Levelized Cost of Hydrogen [$/kg]", loc="center")
# cbar_title.set_rotation = 90

plt.semilogy()

plt.contour(x_axis_pts * 100, y_axis_pts, np.exp(z_surf), levels=[1.5])
plt.grid("on")

plt.xlim((0, 100))
plt.ylim((1000, 100000))

plt.title("Natural GeoH2, Drill Depth = 300m")
plt.xlabel("Wellhead Hydrogen Concentration [mol %]")
plt.ylabel("Initial Wellhead Flow [kg/hr]")

plt.text(60, 2000, "LCOH = $1.50/kg\n(Conventional H2 cost)")

# plt.plot(97.4,35,'md')
# msg = "Mali Bourakébougou H2 Well"
# plt.text(95,35,msg,horizontalalignment="right")

plt.show()
