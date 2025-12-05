from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from attrs import field, define
from scipy.optimize import curve_fit

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.converters.hydrogen.geologic.h2_well_surface_baseclass import (
    GeoH2SurfaceCostConfig,
    GeoH2SurfaceCostBaseClass,
    GeoH2SurfacePerformanceConfig,
    GeoH2SurfacePerformanceBaseClass,
)


ROOT_DIR = Path(__file__).resolve().parent


def scale_inputs(input_vars):
    """
    Scale inputs to be within a range of zero to 1 (only use if inputs are inherently positive)
    """

    scaled_inputs = []
    scale_factors = []
    for input_var in input_vars:
        scale_factor = np.max(input_var)
        scaled_inputs.append(input_var / scale_factor)
        scale_factors.append(scale_factor)

    return scaled_inputs, scale_factors


def exp_power(xy, a1, a2, a3, a4, a5):
    """
    Defines a two-variable fitting function to fit performance and costs curves,
    With the first variable fit to an exponential function and the second to a power function.
    """

    x, y = xy

    return a1 * np.exp(x * a2) + a3 * y**a4 + a5


def double_exp(xy, a1, a2, a3, a4, a5):
    """
    Defines a two-variable fitting function to fit performance and costs curves,
    With the first variable fit to an exponential function and the second to a power function.
    """

    x, y = xy

    return a1 * x**a2 + a3 * x**a4 + a5


def refit_coeffs(input_fn, coeff_fn, output_names, plot_flag=False):
    """
    Fits perfomance and cost coefficients to ASPEN modeling data for surface processing model
    This fits three-dimensional surfaces with two inputs and one output.
    The inputs are hydrogen concentration at the wellhead and capacity of wellhead gas flow.
    The output cycles through the list given in output names.
    """

    # Load .csv with ASPEN results
    path = ROOT_DIR / "inputs"
    inputs_df = pd.read_csv(path / input_fn, index_col=[0, 1], header=0)

    # Curve inputs are wellhead mass flow and H2 concentration, outputs are in `output_names`
    h2_conc = inputs_df.loc["H2 Conc Wellhead"].values.ravel()
    flow = inputs_df.loc["Mass Flow Wellhead"].values.ravel()
    # Add flow as the first output so it can be applied to all the plots
    output_names = ["H2 Flow Out [kg/hr]", *output_names]
    outputs = []
    for name in output_names:
        output = inputs_df.loc[name].values.ravel()
        # All data except output concentration is fit per unit of mass flow at the wellhead
        if "H2 Conc" not in name:
            output = output / flow
            if "H2 Flow" in name:
                h2_out = output * flow
        outputs.append(output)

    # Scale this curve inputs to condition the curve fit
    scaled_inputs, in_scale_factors = scale_inputs([h2_conc, flow])
    scaled_outputs, out_scale_factors = scale_inputs(outputs)
    fit_input_data = np.vstack(scaled_inputs)

    # Data points 0-4 are from Aspen modeling
    # Data points 5 and 6 at H2 conc. = 100% and 0% are correlated empirically from the others
    # These are used to constrain certain fits in the high and low H2 conc. ares, but are not
    # needed for others, so two down-selected sets of fitting data are created here.
    fit_input_data_5 = fit_input_data[:, :5]
    fit_input_data_6 = fit_input_data[:, :6]

    # Create data structure to hold fit parameters
    col_names = [
        "a1",
        "a2",
        "a3",
        "a4",
        "a5",
        "scale_x",
        "scale_y",
        "scale_z",
        "fit_type",
    ]
    fit_coeffs = pd.DataFrame([], columns=col_names)
    labels = []
    h2_out_surf = None

    for i, output in enumerate(outputs):
        name = output_names[i]
        scaled_output = scaled_outputs[i]

        # Perform curve fitting on scaled inputs & output
        if name == "H2 Flow Out [kg/hr]":
            fit_type = "double_exp"
            opt_coeffs, _ = curve_fit(double_exp, fit_input_data_6, scaled_output[:6], ftol=0.0001)
        elif name in ["H2 Conc Out [% mol]", "Labor [op/shift]"]:
            fit_type = "double_exp"
            opt_coeffs, _ = curve_fit(double_exp, fit_input_data_5, scaled_output[:5], ftol=0.0001)
        elif name == "Capex [USD]":
            fit_type = "exp_power"
            opt_coeffs, _ = curve_fit(exp_power, fit_input_data, scaled_output, ftol=0.0001)
        elif name in ["Electricity [kW]", "Cooling Water [kt/h]"]:
            fit_type = "exp_power"
            opt_coeffs, _ = curve_fit(exp_power, fit_input_data_6, scaled_output[:6], ftol=0.0001)
        else:  # Steam
            fit_type = "none"
            opt_coeffs, _ = curve_fit(exp_power, fit_input_data_5, scaled_output[:5], ftol=0.0001)

        # Append coefficients to output structure
        new_coeff_row = list(opt_coeffs)
        new_coeff_row.extend(in_scale_factors)
        new_coeff_row.append(out_scale_factors[i])
        new_coeff_row.append(fit_type)
        fit_coeffs = pd.concat(
            [fit_coeffs, pd.DataFrame([new_coeff_row], index=[name], columns=fit_coeffs.columns)]
        )

        if "H2 Conc Out" not in name:
            label = name[:-1] + "/(kg/hr H2 in)]"
        else:
            label = name
        labels.append(label)

        if plot_flag:
            # Create an input grid
            x_axis_pts = np.arange(0.01, 1, 0.01)
            y_axis_pts = np.exp(np.linspace(np.log(1000), np.log(100000), 100))
            x_grid, y_grid = np.meshgrid(x_axis_pts, y_axis_pts)

            # Scale the input grid
            x_grid_scaled = x_grid / in_scale_factors[0]
            y_grid_scaled = y_grid / in_scale_factors[1]

            # Plot a surface (per unit of H2 flow out if relevant
            if name in ["H2 Flow Out [kg/hr]", "H2 Conc Out [% mol]", "Labor [op/shift]"]:
                z_surf_scaled = double_exp((x_grid_scaled, y_grid_scaled), *opt_coeffs)
            else:
                z_surf_scaled = exp_power((x_grid_scaled, y_grid_scaled), *opt_coeffs)
            z_surf = z_surf_scaled * out_scale_factors[i]
            if name == "H2 Flow Out [kg/hr]":
                h2_out_surf = z_surf * y_grid
            elif name == "Steam [kt/h]":
                z_surf = 0.61 / h2_out_surf
            elif name != "H2 Conc Out [% mol]":
                if h2_out_surf is not None:
                    z_surf = z_surf * y_grid / h2_out_surf
            cplot = plt.contourf(x_axis_pts, y_axis_pts, z_surf, cmap="turbo", levels=256)

            # Plot data points to check surface fit
            cmap_min = np.min(cplot.levels)
            cmap_max = np.max(cplot.levels)
            for point_ind, point in enumerate(output[:5]):
                if name not in ["H2 Flow Out [kg/hr]", "H2 Conc Out [% mol]"]:
                    point *= flow[point_ind] / h2_out[point_ind]
                point_color_frac = (point - cmap_min) / (cmap_max - cmap_min)
                plt.plot(
                    h2_conc[point_ind],
                    flow[point_ind],
                    "o",
                    zorder=1,
                    color=cplot.cmap(point_color_frac)[:3],
                    markeredgecolor=[1, 1, 1],
                )

            if "H2 Conc Out" not in name:
                label = label[:-4] + "out)]"
            plt.title(label)
            plt.xlabel("Wellhead Hydrogen Concentration [mol %]")
            plt.ylabel("Wellhead Flow Capacity [kg/hr]")
            cbar = plt.colorbar()
            cbar.set_label(label, loc="center")
            plt.semilogy()
            plt.show()

    # Lop off first row with flow
    fit_coeffs.index = labels
    fit_coeffs = fit_coeffs.iloc[1:]

    # Save coeffs to file
    fit_coeffs.to_csv(path / coeff_fn)

    # Output as dict
    coeff_dict = dict(zip(labels[1:], fit_coeffs.to_dict("records")))

    return coeff_dict


def load_coeffs(coeff_fn, output_names):
    # Load .csv with pre-fit coefficients
    df = pd.read_csv(ROOT_DIR / "inputs" / coeff_fn, index_col=0)

    # Output as dict
    coeff_dict = {}
    for name in output_names:
        ds = df.loc[name]
        coeff_dict[name] = dict(zip(df.columns.values, ds.values))

    return coeff_dict


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

        perf_coeff_fn (str):
            Filename of performance curve coefficients. Will be loaded if `refit_coeffs`
            is False and overwritten if `refit_coeffs` is True. Located in the ./inputs directory.
    """

    refit_coeffs: bool = field()
    curve_input_fn: str = field()
    perf_coeff_fn: str = field()


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
        perf_coeffs (dict):
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

        if self.config.refit_coeffs:
            output_names = [
                "H2 Flow Out [kg/hr]",
                "H2 Conc Out [% mol]",
                "Electricity [kW]",
                "Cooling Water [kt/h]",
                "Steam [kt/h]",
            ]
            coeffs = refit_coeffs(
                self.config.curve_input_fn, self.config.perf_coeff_fn, output_names
            )
        else:
            output_names = [
                "H2 Flow Out [kg/hr/(kg/hr H2 in)]",
                "H2 Conc Out [% mol]",
                "Electricity [kW/(kg/hr H2 in)]",
                "Cooling Water [kt/h/(kg/hr H2 in)]",
                "Steam [kt/h/(kg/hr H2 in)]",
            ]
            coeffs = load_coeffs(self.config.perf_coeff_fn, output_names)

        self.add_input("max_wellhead_gas", val=-1.0)
        self.add_discrete_input("perf_coeffs", val=coeffs)

        self.add_output("electricity_consumed", val=-1.0, shape=(n_timesteps,))
        self.add_output("water_consumed", val=-1.0, shape=(n_timesteps,))
        self.add_output("steam_out", val=-1.0, shape=(n_timesteps,))

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # Parse inputs
        perf_coeffs = discrete_inputs["perf_coeffs"]
        wellhead_flow_kg_hr = inputs["wellhead_gas_in"]
        wellhead_cap_kg_hr = inputs["max_flow_in"]
        if self.config.size_from_wellhead_flow:
            wellhead_cap_kg_hr = np.max(wellhead_flow_kg_hr)
        wellhead_h2_conc = inputs["wellhead_h2_concentration_mol"] / 100
        outputs["max_flow_size"] = wellhead_cap_kg_hr

        # Calculate performance curves
        curve_names = [
            "H2 Flow Out [kg/hr/(kg/hr H2 in)]",
            "H2 Conc Out [% mol]",
            "Electricity [kW/(kg/hr H2 in)]",
            "Cooling Water [kt/h/(kg/hr H2 in)]",
            "Steam [kt/h/(kg/hr H2 in)]",
        ]
        curve_results = {}
        for curve_name in curve_names:
            x = wellhead_h2_conc / perf_coeffs[curve_name]["scale_x"]
            y = wellhead_cap_kg_hr / perf_coeffs[curve_name]["scale_y"]
            flow_out_coeffs = [perf_coeffs[curve_name][i] for i in ["a1", "a2", "a3", "a4", "a5"]]
            fit_type = perf_coeffs[curve_name]["fit_type"]
            if fit_type == "double_exp":
                z = double_exp((x, y), *flow_out_coeffs)
            elif fit_type == "exp_power":
                z = exp_power((x, y), *flow_out_coeffs)
            else:  # Steam
                z = 0
            curve_results[curve_name] = z * perf_coeffs[curve_name]["scale_z"]

        # Parse outputs
        h2_out_kg_hr = curve_results["H2 Flow Out [kg/hr/(kg/hr H2 in)]"] * wellhead_flow_kg_hr
        h2_out_conc = curve_results["H2 Conc Out [% mol]"]
        elec_in_kw = curve_results["Electricity [kW/(kg/hr H2 in)]"] * wellhead_flow_kg_hr
        water_in_kt_h = curve_results["Cooling Water [kt/h/(kg/hr H2 in)]"] * wellhead_flow_kg_hr
        steam_out_kt_h = 0.61  # Little variance between Aspen results, setting constant for now
        outputs["hydrogen_out"] = h2_out_kg_hr
        outputs["hydrogen_concentration_out"] = h2_out_conc
        outputs["electricity_consumed"] = elec_in_kw
        outputs["water_consumed"] = water_in_kt_h
        outputs["steam_out"] = steam_out_kt_h
        outputs["total_hydrogen_produced"] = np.sum(h2_out_kg_hr)


@define
class AspenGeoH2SurfaceCostConfig(GeoH2SurfaceCostConfig):
    """Configuration for cost parameters for a natural geologic hydrogen well surface
    processing system. This class defines cost parameters specific to **natural** geologic
    hydrogen systems (as opposed to stimulated systems).

    Inherits from:
        GeoH2SurfaceCostConfig

    Attributes:
        refit_coeffs (bool):
            Whether to re-fit performance curves to ASPEN data

        curve_input_fn (str):
            Filename of ASPEN model results file used to generate curve fits. Only used if
            `refit_coeffs` is True. Must be located in the ./inputs directory.

        cost_coeff_fn (str):
            Filename of cost curve coefficients. Will be loaded if `refit_coeffs`
            is False and overwritten if `refit_coeffs` is True. Located in the ./inputs directory.

        op_labor_rate (float):
            Cost of operational labor in $/hr

        overhead_rate (float):
            Fraction of operational labor opex seen in overhead opex

        electricity_price (float):
            Price of electricity in USD/kWh

        water_price (float):
            Price of water in USD/kt
    """

    refit_coeffs: bool = field()
    curve_input_fn: str = field()
    cost_coeff_fn: str = field()
    op_labor_rate: float = field()
    overhead_rate: float = field()
    electricity_price: float = field()
    water_price: float = field()


class AspenGeoH2SurfaceCostModel(GeoH2SurfaceCostBaseClass):
    """OpenMDAO component for modeling the cost of a surface processing system for a
        natural geologic hydrogen plant.

    This component estimates hydrogen production cost for **naturally occurring**
    geologic hydrogen systems.

    The modeling approach is informed by the following studies:
        - Mathur et al. (Stanford): https://doi.org/10.31223/X5599G

    Attributes:
        config (NaturalGeoH2CostConfig):
            Configuration object containing model parameters specific to natural geologic
            hydrogen systems.

    Inputs:
        cost_coeffs (dict):
            Performance curve coefficients, structured like so:
            {"<output name>": [<list, of, curve, coefficients>]}

        op_labor_rate (float):
            Cost of operational labor in $/hr

        overhead_rate (float):
            Fraction of operational labor opex seen in overhead opex

        electricity_price (float):
            Price of electricity in USD/kWh

        water_price (float):
            Price of water in USD/kt

        electricity_consumed (ndarray):
            Hourly electricity consumption profile (8760 hours), in kW.

        water_consumed (ndarray):
            Hourly water consumption profile (8760 hours), in kg/h.

    Outputs:
        All inherited from GeoH2SurfaceCostBaseClass
    """

    def setup(self):
        self.config = AspenGeoH2SurfaceCostConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        if self.config.refit_coeffs:
            output_names = ["Capex [USD]", "Labor [op/shift]"]
            coeffs = refit_coeffs(
                self.config.curve_input_fn, self.config.cost_coeff_fn, output_names
            )
        else:
            output_names = [
                "Capex [USD/(kg/hr H2 in)]",
                "Labor [op/shift/(kg/hr H2 in)]",
            ]
            coeffs = load_coeffs(self.config.cost_coeff_fn, output_names)

        self.add_discrete_input("cost_coeffs", val=coeffs)

        self.add_input("op_labor_rate", val=self.config.op_labor_rate, units="USD/h")
        self.add_input("overhead_rate", val=self.config.overhead_rate, units="unitless")
        self.add_input("electricity_price", val=self.config.electricity_price, units="USD/kW/h")
        self.add_input("water_price", val=self.config.water_price, units="USD/kt")
        self.add_input("electricity_consumed", val=-1.0, shape=(n_timesteps,))
        self.add_input("water_consumed", val=-1.0, shape=(n_timesteps,))

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        if self.config.cost_from_fit:
            # Parse inputs
            cost_coeffs = discrete_inputs["cost_coeffs"]
            wellhead_cap_kg_hr = inputs["max_flow_size"]
            wellhead_h2_conc = inputs["wellhead_hydrogen_concentration"] / 100
            op_labor_rate = inputs["op_labor_rate"]
            overhead_rate = inputs["overhead_rate"]
            electricity_price = inputs["electricity_price"]
            water_price = inputs["water_price"]
            electricity_consumed = inputs["electricity_consumed"]
            water_consumed = inputs["water_consumed"]

            # Calculate performance curves
            curve_names = [
                "Capex [USD/(kg/hr H2 in)]",
                "Labor [op/shift/(kg/hr H2 in)]",
            ]
            curve_results = {}
            for curve_name in curve_names:
                x = wellhead_h2_conc / cost_coeffs[curve_name]["scale_x"]
                y = wellhead_cap_kg_hr / cost_coeffs[curve_name]["scale_y"]
                flow_out_coeffs = [
                    cost_coeffs[curve_name][i] for i in ["a1", "a2", "a3", "a4", "a5"]
                ]
                fit_type = cost_coeffs[curve_name]["fit_type"]
                if fit_type == "double_exp":
                    z = double_exp((x, y), *flow_out_coeffs)
                elif fit_type == "exp_power":
                    z = exp_power((x, y), *flow_out_coeffs)
                else:  # Steam
                    z = 0
                curve_results[curve_name] = z * cost_coeffs[curve_name]["scale_z"]

            # Parse outputs
            capex_usd = curve_results["Capex [USD/(kg/hr H2 in)]"] * wellhead_cap_kg_hr
            # labor_op_shift = curve_results["Labor [op/shift/(kg/hr H2 in)]"] * wellhead_cap_kg_hr
            outputs["CapEx"] = capex_usd

            # Calculate opex
            labor_usd_year = 5 * 8760 * op_labor_rate  # ignoring labor_op_shift for now
            overhead_usd_year = labor_usd_year * overhead_rate
            outputs["OpEx"] = labor_usd_year + overhead_usd_year

            # Calculate variable opex
            elec_varopex = np.sum(electricity_consumed) * electricity_price
            water_varopex = np.sum(water_consumed) * water_price
            outputs["VarOpEx"] = elec_varopex + water_varopex

        else:
            outputs["CapEx"] = inputs["custom_capex"]
            outputs["OpEx"] = inputs["custom_opex"]


if __name__ == "__main__":
    output_names = [
        "H2 Flow Out [kg/hr]",
        "H2 Conc Out [% mol]",
        "Electricity [kW]",
        "Cooling Water [kt/h]",
        "Steam [kt/h]",
    ]
    coeffs = refit_coeffs("aspen_results.csv", "aspen_perf_coeffs.csv", output_names, True)
    output_names = ["Capex [USD]", "Labor [op/shift]"]
    coeffs = refit_coeffs("aspen_results.csv", "aspen_cost_coeffs.csv", output_names, True)
