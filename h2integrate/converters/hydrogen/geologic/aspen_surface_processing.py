from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from attrs import field, define
from scipy.optimize import curve_fit

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.converters.hydrogen.geologic.h2_well_surface_baseclass import (
    GeoH2SurfacePerformanceConfig,
    GeoH2SurfacePerformanceBaseClass,
)


ROOT_DIR = Path(__file__).resolve().parent


@define
class AspenGeoH2SurfacePerformanceConfig(GeoH2SurfacePerformanceConfig):
    """Configuration for performance parameters for a natural geologic hydrogen well surface
    processing system. This class defines performance parameters specific to **natural** geologic
    hydrogen systems (as opposed to stimulated systems).

    Inherits from:
        GeoH2SurfacePerformanceConfig

    Attributes:
        refit_coeffs (bool):
            Whether to re-fit performance curves to ASPEN data

        curve_input_fn (str):
            Filename of ASPEN model results file used to generate curve fits. Only used if
            `refit_coeffs` is True. Must be located in the ./inputs directory.

        curve_coeff_fn (str):
            Filename of performance (and cost) curve coefficients. Will be loaded if `refit_coeffs`
            is False and overwritten if `refit_coeffs` is True. Located in the ./inputs directory.
    """

    refit_coeffs: bool = field()
    curve_input_fn: str = field()
    curve_coeff_fn: str = field()


def double_exp(xy, a1, a2, a3, a4):  # , a5):
    """
    Defines a two-variable exponential fitting function to fit performance and costs curves
    """

    x, y = xy

    return a1 * np.exp(x * a2) + a3 * y**a4  # + a5


def double_log(xy, a1, a2, a3):  # , a4, a5, a6):
    x, y = xy

    return (
        a1
        + a2 * np.log(x)  # ** a4
        + a3 * np.log(y)  # ** a5
        # + a4 * np.log(x) ** 2
        # + a5 * np.log(x) * np.log(y)
        # + a6 * np.log(y) ** 2
    )


def refit_coeffs(input_fn, coeff_fn, output_names, plot_flag=False):
    """
    Fits perfomance and cost coefficients to ASPEN modeling data for surface processing model
    This fits three-dimensional surfaces with two inputs and one output.
    The inputs are hydrogen concentration at the wellhead and capacity of wellhead gas flow.
    The output cycles through the list given in output names.
    """

    # Load .csv with ASPEN results
    inputs_df = pd.read_csv(ROOT_DIR / "inputs" / input_fn, index_col=[0, 1], header=0)

    # Curve inputs are wellhead mass flow and H2 concentration
    h2_conc = inputs_df.loc["H2 Conc Wellhead"].values.ravel()
    flow = inputs_df.loc["Mass Flow Wellhead"].values.ravel() / 1e5
    input_data = np.vstack((h2_conc, flow))

    for name in output_names:
        out_data = inputs_df.loc[name].values.ravel()

        # All data except output concentration is fit per unit of mass flow at the wellhead
        if "H2 Conc" not in name:
            fit_data = out_data / flow
        else:
            fit_data = out_data

        opt_coeffs, _ = curve_fit(double_exp, input_data, fit_data, ftol=0.001, xtol=0.001)

        if plot_flag:
            # Create a grid
            x_axis_pts = np.arange(0.01, 1, 0.01)
            y_axis_pts = np.exp(np.linspace(np.log(5000 / 1e5), np.log(100000 / 1e5), 100))
            x_grid, y_grid = np.meshgrid(x_axis_pts, y_axis_pts)

            # Plot a surface
            z_surf = double_exp((x_grid, y_grid), *opt_coeffs)
            if "H2 Conc" not in name:
                fit_surf = z_surf / 1e5
            else:
                fit_surf = z_surf
            cplot = plt.contourf(x_axis_pts, y_axis_pts * 1e5, fit_surf, cmap="turbo", levels=256)

            # Plot data points to check surface fit
            cmap_min = np.min(cplot.levels)
            cmap_max = np.max(cplot.levels)
            for point_ind, point in enumerate(fit_data / 1e5):
                point_color_frac = (point - cmap_min) / (cmap_max - cmap_min)
                plt.plot(
                    h2_conc[point_ind],
                    flow[point_ind] * 1e5,
                    "o",
                    zorder=1,
                    color=cplot.cmap(point_color_frac)[:3],
                    markeredgecolor=[1, 1, 1],
                )

            if "H2 Conc Out" not in name:
                label = name[:-1] + "/(kg/hr)]"
            else:
                label = name
            plt.title(label)
            plt.xlabel("Wellhead Hydrogen Concentration [mol %]")
            plt.ylabel("Wellhead Flow Capacity [kg/hr]")
            cbar = plt.colorbar()
            cbar.set_label(label, loc="center")
            plt.show()


def load_coeffs():
    pass


class AspenGeoH2SurfacePerformanceModel(GeoH2SurfacePerformanceBaseClass):
    """OpenMDAO component for modeling the performance of a surface processing system for a
        natural geologic hydrogen plant.

    This component estimates hydrogen production performance for **naturally occurring**
    geologic hydrogen systems.

    The modeling approach is informed by the following studies:
        - Mathur et al. (Stanford): https://doi.org/10.31223/X5599G

    Attributes:
        config (NaturalGeoH2PerformanceConfig):
            Configuration object containing model parameters specific to natural geologic
            hydrogen systems.

    Inputs:
        curve_coeffs (dict):
            Performance curve coefficients, structured like so:
            {"<output name>": [<list, of, curve, coefficients>]}

    Outputs:
        electricity_consumed (ndarray):
            Hourly electricity consumption profile (8760 hours), in kW.

        water_consumed (ndarray):
            Hourly water consumption profile (8760 hours), in kg/h.

        steam_out (ndarray):
            Hourly steam production profile (8760 hours), in kW thermal.
    """

    def setup(self):
        self.config = AspenGeoH2SurfacePerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        super().setup()
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        output_names = [
            "H2 Flow Out",
            "H2 Conc Out",
            "Electricity",
            "Cooling Water",
            "Steam",
        ]
        if self.config.refit_coeffs:
            coeffs = refit_coeffs(
                self.config.curve_input_fn, self.config.curve_coeff_fn, output_names
            )
        else:
            coeffs = load_coeffs(self.config.curve_coeff_fn, output_names)

        self.add_discrete_input("curve_coeffs", val=coeffs)

        self.add_output("electricity_consumed", val=-1.0, shape=(n_timesteps,))
        self.add_output("water_consumed", val=-1.0, shape=(n_timesteps,))
        self.add_output("steam_out", val=-1.0, shape=(n_timesteps,))

    def compute(self):
        pass


if __name__ == "__main__":
    output_names = [
        "H2 Flow Out [kg/hr]",  # working
        "H2 Conc Out [% mol]",
        "Capex [USD]",
        "Electricity [kW]",
        "Cooling Water [kt/h]",  # working
        "Steam [klb/h]",  # working
        "Labor [op/shift]",  # working
    ]
    refit_coeffs("Aspen_Cost_Results_simple.csv", "", output_names, True)
