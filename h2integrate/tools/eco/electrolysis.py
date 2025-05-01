import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker

from h2integrate.tools.eco.utilities import ceildiv
from h2integrate.simulation.technologies.hydrogen.electrolysis.run_h2_PEM import run_h2_PEM
from h2integrate.simulation.technologies.hydrogen.electrolysis.pem_mass_and_footprint import (
    mass as run_electrolyzer_mass,
    footprint as run_electrolyzer_footprint,
)


def run_electrolyzer_physics(
    hopp_results,
    h2integrate_config,
    wind_resource,
    design_scenario,
    show_plots=False,
    save_plots=False,
    output_dir="./output/",
    verbose=False,
):
    if isinstance(output_dir, str):
        output_dir = Path(output_dir).resolve()
    electrolyzer_size_mw = h2integrate_config["electrolyzer"]["rating"]
    electrolyzer_capex_kw = h2integrate_config["electrolyzer"]["electrolyzer_capex"]

    # IF GRID CONNECTED
    if h2integrate_config["project_parameters"]["grid_connection"]:
        # NOTE: if grid-connected, it assumes that hydrogen demand is input and there is not
        # multi-cluster control strategies. This capability exists at the cluster level, not at the
        # system level.
        if h2integrate_config["electrolyzer"]["sizing"]["hydrogen_dmd"] is not None:
            grid_connection_scenario = "grid-only"
            hydrogen_production_capacity_required_kgphr = h2integrate_config["electrolyzer"][
                "sizing"
            ]["hydrogen_dmd"]
            energy_to_electrolyzer_kw = []
        else:
            grid_connection_scenario = "off-grid"
            hydrogen_production_capacity_required_kgphr = []
            energy_to_electrolyzer_kw = np.ones(8760) * electrolyzer_size_mw * 1e3
    # IF NOT GRID CONNECTED
    else:
        hydrogen_production_capacity_required_kgphr = []
        grid_connection_scenario = "off-grid"
        energy_to_electrolyzer_kw = np.asarray(
            hopp_results["combined_hybrid_power_production_hopp"]
        )

    n_pem_clusters = int(
        ceildiv(
            round(electrolyzer_size_mw, 1), h2integrate_config["electrolyzer"]["cluster_rating_MW"]
        )
    )

    electrolyzer_real_capacity_kW = (
        n_pem_clusters * h2integrate_config["electrolyzer"]["cluster_rating_MW"] * 1e3
    )

    if np.abs(electrolyzer_real_capacity_kW - (electrolyzer_size_mw * 1e3)) > 1.0:
        electrolyzer_real_capacity_mw = electrolyzer_real_capacity_kW / 1e3
        cluster_cap_mw = h2integrate_config["electrolyzer"]["cluster_rating_MW"]
        msg = (
            f"setting electrolyzer capacity to {electrolyzer_real_capacity_mw} MW. "
            f"Input value of {electrolyzer_size_mw:.2f} MW is not a "
            f"multiple of cluster capacity ({cluster_cap_mw} MW)"
        )
        warnings.warn(msg, UserWarning)
    ## run using greensteel model
    pem_param_dict = {
        "eol_eff_percent_loss": h2integrate_config["electrolyzer"]["eol_eff_percent_loss"],
        "uptime_hours_until_eol": h2integrate_config["electrolyzer"]["uptime_hours_until_eol"],
        "include_degradation_penalty": h2integrate_config["electrolyzer"][
            "include_degradation_penalty"
        ],
        "turndown_ratio": h2integrate_config["electrolyzer"]["turndown_ratio"],
    }

    if "water_usage_gal_pr_kg" in h2integrate_config["electrolyzer"]:
        pem_param_dict.update(
            {"water_usage_gal_pr_kg": h2integrate_config["electrolyzer"]["water_usage_gal_pr_kg"]}
        )
    if "curve_coeff" in h2integrate_config["electrolyzer"]:
        pem_param_dict.update({"curve_coeff": h2integrate_config["electrolyzer"]["curve_coeff"]})

    if "time_between_replacement" in h2integrate_config["electrolyzer"]:
        msg = (
            "`time_between_replacement` as an input is deprecated. It is now calculated internally"
            " and is output in electrolyzer_physics_results['H2_Results']['Time Until Replacement"
            " [hrs]']."
        )
        warnings.warn(msg)

    H2_Results, h2_ts, h2_tot, power_to_electrolyzer_kw = run_h2_PEM(
        electrical_generation_timeseries=energy_to_electrolyzer_kw,
        electrolyzer_size=electrolyzer_size_mw,
        useful_life=h2integrate_config["project_parameters"][
            "project_lifetime"
        ],  # EG: should be in years for full plant life - only used in financial model
        n_pem_clusters=n_pem_clusters,
        pem_control_type=h2integrate_config["electrolyzer"]["pem_control_type"],
        electrolyzer_direct_cost_kw=electrolyzer_capex_kw,
        user_defined_pem_param_dictionary=pem_param_dict,
        grid_connection_scenario=grid_connection_scenario,  # if not offgrid, assumes steady h2 demand in kgphr for full year  # noqa: E501
        hydrogen_production_capacity_required_kgphr=hydrogen_production_capacity_required_kgphr,
        debug_mode=False,
        verbose=verbose,
    )

    # calculate mass and foorprint of system
    mass_kg = run_electrolyzer_mass(electrolyzer_size_mw)
    footprint_m2 = run_electrolyzer_footprint(electrolyzer_size_mw)

    # store results for return
    H2_Results.update({"system capacity [kW]": electrolyzer_real_capacity_kW})
    electrolyzer_physics_results = {
        "H2_Results": H2_Results,
        "capacity_factor": H2_Results["Life: Capacity Factor"],
        "equipment_mass_kg": mass_kg,
        "equipment_footprint_m2": footprint_m2,
        "power_to_electrolyzer_kw": power_to_electrolyzer_kw,
    }

    if verbose:
        print("\nElectrolyzer Physics:")  # 61837444.34555772 145297297.29729727
        print(
            "H2 Produced Annually (metric tons): ",
            H2_Results["Life: Annual H2 production [kg/year]"] * 1e-3,
        )
        print(
            "Max H2 hourly (metric tons): ",
            max(H2_Results["Hydrogen Hourly Production [kg/hr]"]) * 1e-3,
        )
        print(
            "Max H2 daily (metric tons): ",
            max(
                np.convolve(
                    H2_Results["Hydrogen Hourly Production [kg/hr]"],
                    np.ones(24),
                    mode="valid",
                )
            )
            * 1e-3,
        )

        prodrate = 1.0 / round(H2_Results["Rated BOL: Efficiency [kWh/kg]"], 2)  # kg/kWh
        roughest = power_to_electrolyzer_kw * prodrate
        print("Energy to electrolyzer (kWh): ", sum(power_to_electrolyzer_kw))
        print(
            "Energy per kg (kWh/kg): ",
            H2_Results["Sim: Total Input Power [kWh]"] / H2_Results["Sim: Total H2 Produced [kg]"],
        )
        print("Max hourly based on est kg/kWh (kg): ", max(roughest))
        print(
            "Max daily rough est (metric tons): ",
            max(np.convolve(roughest, np.ones(24), mode="valid")) * 1e-3,
        )
        print(
            "Electrolyzer Life Average Capacity Factor: ",
            H2_Results["Life: Capacity Factor"],
        )

    if save_plots or show_plots:
        N = 24 * 7 * 4
        fig, ax = plt.subplots(3, 2, sharex=True, sharey="row")

        wind_speed = [W[2] for W in wind_resource._data["data"]]

        # plt.title("4-week running average")
        pad = 5
        ax[0, 0].annotate(
            "Hourly",
            xy=(0.5, 1),
            xytext=(0, pad),
            xycoords="axes fraction",
            textcoords="offset points",
            size="large",
            ha="center",
            va="baseline",
        )
        ax[0, 1].annotate(
            "4-week running average",
            xy=(0.5, 1),
            xytext=(0, pad),
            xycoords="axes fraction",
            textcoords="offset points",
            size="large",
            ha="center",
            va="baseline",
        )

        ax[0, 0].plot(wind_speed)
        convolved_wind_speed = np.convolve(wind_speed, np.ones(N) / (N), mode="valid")
        ave_x = range(N, len(convolved_wind_speed) + N)

        ax[0, 1].plot(ave_x, convolved_wind_speed)
        ax[0, 0].set(ylabel="Wind\n(m/s)", ylim=[0, 30], xlim=[0, len(wind_speed)])
        tick_spacing = 10
        ax[0, 0].yaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

        y = h2integrate_config["electrolyzer"]["rating"]
        ax[1, 0].plot(energy_to_electrolyzer_kw * 1e-3)
        ax[1, 0].axhline(y=y, color="r", linestyle="--", label="Nameplate Capacity")

        convolved_energy_to_electrolyzer = np.convolve(
            energy_to_electrolyzer_kw * 1e-3, np.ones(N) / (N), mode="valid"
        )

        ax[1, 1].plot(
            ave_x,
            convolved_energy_to_electrolyzer,
        )
        ax[1, 1].axhline(y=y, color="r", linestyle="--", label="Nameplate Capacity")
        ax[1, 0].set(ylabel="Electrolyzer \nPower (MW)", ylim=[0, 500], xlim=[0, len(wind_speed)])
        # ax[1].legend(frameon=False, loc="best")
        tick_spacing = 200
        ax[1, 0].yaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
        ax[1, 0].text(1000, y + 0.1 * tick_spacing, "Electrolyzer Rating", color="r")

        ax[2, 0].plot(
            electrolyzer_physics_results["H2_Results"]["Hydrogen Hourly Production [kg/hr]"] * 1e-3
        )
        convolved_hydrogen_production = np.convolve(
            electrolyzer_physics_results["H2_Results"]["Hydrogen Hourly Production [kg/hr]"] * 1e-3,
            np.ones(N) / (N),
            mode="valid",
        )
        ax[2, 1].plot(
            ave_x,
            convolved_hydrogen_production,
        )
        tick_spacing = 2
        ax[2, 0].set(
            xlabel="Hour",
            ylabel="Hydrogen\n(metric tons/hr)",
            # ylim=[0, 7000],
            xlim=[0, len(H2_Results["Hydrogen Hourly Production [kg/hr]"])],
        )
        ax[2, 0].yaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

        ax[2, 1].set(
            xlabel="Hour",
            # ylim=[0, 7000],
            xlim=[
                4 * 7 * 24 - 1,
                len(H2_Results["Hydrogen Hourly Production [kg/hr]"] + 4 * 7 * 24 + 2),
            ],
        )
        ax[2, 1].yaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

        plt.tight_layout()
        if save_plots:
            savepaths = [
                output_dir / "figures/production/",
                output_dir / "data/",
            ]
            for savepath in savepaths:
                if not savepath.exists():
                    savepath.mkdir(parents=True)
            plt.savefig(
                savepaths[0] / f"production_overview_{design_scenario['id']}.png",
                transparent=True,
            )
            pd.DataFrame.from_dict(
                data={
                    "Hydrogen Hourly Production [kg/hr]": H2_Results[
                        "Hydrogen Hourly Production [kg/hr]"
                    ],
                    "Hourly Water Consumption [kg/hr]": electrolyzer_physics_results["H2_Results"][
                        "Water Hourly Consumption [kg/hr]"
                    ],
                }
            ).to_csv(savepaths[1] / f"h2_flow_{design_scenario['id']}.csv")
        if show_plots:
            plt.show()

    return electrolyzer_physics_results
