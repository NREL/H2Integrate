from __future__ import annotations

import os
import copy
import warnings
from typing import Any
from pathlib import Path

import yaml
import numpy as np
import pandas as pd


pd.options.mode.chained_assignment = None  # default='warn'

import matplotlib.pyplot as plt
from attrs import field, define, fields


pd.options.mode.chained_assignment = None  # default='warn'

from ProFAST import ProFAST
from hopp.utilities import load_yaml
from hopp.simulation import HoppInterface

import h2integrate.tools.eco.finance as he_fin
import h2integrate.tools.eco.hopp_mgmt as he_hopp
import h2integrate.tools.eco.utilities as he_util
import h2integrate.tools.eco.electrolysis as he_elec
import h2integrate.tools.eco.hydrogen_mgmt as he_h2
import h2integrate.tools.profast_reverse_tools as rev_pf_tools
import h2integrate.tools.h2integrate_sim_file_utils as gh_fio
from h2integrate.tools.eco.utilities import calculate_lca
from h2integrate.simulation.technologies.iron.iron import (
    IronCostModelOutputs,
    IronFinanceModelOutputs,
    IronPerformanceModelOutputs,
    run_iron_full_model,
)
from h2integrate.simulation.technologies.steel.steel import (
    SteelCostModelOutputs,
    SteelFinanceModelOutputs,
    SteelCapacityModelOutputs,
    run_steel_full_model,
)
from h2integrate.simulation.technologies.ammonia.ammonia import (
    AmmoniaCostModelOutputs,
    AmmoniaFinanceModelOutputs,
    AmmoniaCapacityModelOutputs,
    run_ammonia_full_model,
)
from h2integrate.simulation.technologies.hydrogen.electrolysis.pem_cost_tools import (
    ElectrolyzerLCOHInputConfig,
)
from h2integrate.simulation.technologies.iron.martin_transport.iron_transport import (
    calc_iron_ship_cost,
)


def convert_to_serializable(value: Any) -> float | int | str | type[None] | list | dict:
    """Recursively converts complex types to JSON/YAML-compatible formats.

    Handles:
    - `np.ndarray` -> list
    - `tuple` -> list
    - `np.generic` (e.g., `np.float64`, `np.int32`) -> corresponding native Python types
    - `pandas.DataFrame` -> list of dicts, recursively processed
    - `pandas.Series` -> list, recursively processed
    - `attrs` objects -> dict of serialized attributes
    - Handles deeply nested structures

    Note: this function was originally created by ChatGPT and edited manually to work as desired

    Args:
        value (Any): value to converted for output to yaml
    Returns:
        Union[float, int, str, type(None), list, dict]: input value in yaml-compatible format
    """

    if isinstance(value, np.generic):
        # Handles NumPy scalar types, converting to python native types
        return value.item()
    if isinstance(value, (np.ndarray, tuple, list, pd.Series)):
        # Recursively convert array-like types
        return [convert_to_serializable(v) for v in value]
    if isinstance(value, dict):
        # recursively convert dictionary values
        return {k: convert_to_serializable(v) for k, v in value.items()}
    if isinstance(value, pd.DataFrame):
        # Recursively convert each cell in the DataFrame
        return [
            {k: convert_to_serializable(v) for k, v in row.items()}
            for row in value.to_dict(orient="records")
        ]
    if hasattr(value, "__attrs_attrs__"):
        # If it's an `attrs` class, recursively convert attributes
        return {
            f.name: convert_to_serializable(getattr(value, f.name)) for f in fields(type(value))
        }
    if isinstance(value, (float, int, str, type(None))):
        # simple native python types do not need conversion
        return value

    # Fall back to string representation for unsupported types
    return str(value)


@define
class H2IntegrateSimulationConfig:
    """
    Class to hold all the configuration parameters for the H2Integrate model

    Also sets up the HOPP, H2Integrate, ORBIT, and FLORIS configurations based on the
    input files and configuration parameters passed in.

    Args:
        filename_hopp_config (str): filename for the HOPP configuration
        filename_config.h2integrate_config (str): filename for the H2Integrate configuration
        filename_turbine_config (str): filename for the turbine configuration
        filename_orbit_config (str): filename for the ORBIT configuration
        filename_floris_config (str): filename for the FLORIS configuration
        electrolyzer_rating_mw (Optional[float]): rating of the electrolyzer in MW
        solar_rating (Optional[float]): rating of the solar plant in MW
        battery_capacity_kw (Optional[float]): capacity of the battery in kW
        battery_capacity_kwh (Optional[float]): capacity of the battery in kWh
        wind_rating (Optional[float]): rating of the wind plant in MW
        verbose (bool): flag to print verbose output
        show_plots (bool): flag to show plots
        save_plots (bool): flag to save plots
        output_dir (str, path): path for saving output files
        use_profast (bool): flag to use profast
        post_processing (bool): flag to run post processing
        storage_type (Optional[str]): type of storage
        incentive_option (int): incentive option
        plant_design_scenario (int): plant design scenario
        output_level (int): output level
        grid_connection (Optional[bool]): flag for grid connection
        run_full_simulation (bool): flag for whether to run the physics simulation (True) or load
            previous results from pickles (False). Only used when running iron simulation
        save_physics_results (bool): flag for whether save the results of physics simulations to
            file for future use
        run_full_simulation_fn (Optional[str]): filename for where to save the physics simulation
        iron_out_fn (Optional[str]): filename for where to save final results
        iron_modular (bool) : flag for whether to run a multi-module iron simulation (True) or
            single-module (False)
        user_lcoh (float): a user-supplied LCOH value [$/kg-H2] to bypass H2 calculations
        user_lcoe (float): a user-supplied LCOE value [$/kWh] to bypass HOPP calculations
        user_annual_wind_kwh_prod (float): user-supplied annual wind kWh produciton to bypass HOPP
        user_annual_pv_kwh_prod (float): user-supplied annual solar PV kWh produciton to bypass HOPP
        user_life_annual_h2_kwh (float): user-supplied annual H2 kWh consumption to bypass H2 calcs
        user_life_annual_h2_prod (float): user-supplied annual H2 kg production to bypass H2 calcs
        save_h2integrate_output (bool): flag for whether to save the final H2I outputs
    """

    filename_hopp_config: str
    filename_h2integrate_config: str
    filename_turbine_config: str
    filename_floris_config: str
    filename_orbit_config: str | None = field(default=None)
    electrolyzer_rating_mw: float | None = field(default=None)
    solar_rating: float | None = field(default=None)
    battery_capacity_kw: float | None = field(default=None)
    battery_capacity_kwh: float | None = field(default=None)
    wind_rating: float | None = field(default=None)
    verbose: bool = field(default=False)
    show_plots: bool = field(default=False)
    save_plots: bool = field(default=False)
    output_dir: str | os.PathLike | None = field(default="output/")
    use_profast: bool = field(default=True)
    post_processing: bool = field(default=True)
    storage_type: str | None = field(default=None)
    incentive_option: int = field(default=1)
    plant_design_scenario: int = field(default=1)
    output_level: int = field(default=8)
    grid_connection: bool | None = field(default=None)
    run_full_simulation: bool = field(default=True)
    save_physics_results: bool = field(default=False)
    run_full_simulation_fn: str | None = field(default=None)
    iron_out_fn: str | None = field(default=None)
    iron_modular: bool = field(default=False)
    user_lcoh: float | None = field(default=None)
    user_lcoe: float | None = field(default=None)
    user_annual_wind_kwh_prod: float | dict | None = field(default=None)
    user_annual_pv_kwh_prod: float | dict | None = field(default=None)
    user_life_annual_h2_kwh: float | dict | None = field(default=None)
    user_life_annual_h2_prod: float | dict | None = field(default=None)
    save_h2integrate_output: bool | None = field(default=False)

    # these are set in the __attrs_post_init__ method
    hopp_config: dict = field(init=False)
    h2integrate_config: dict = field(init=False)
    orbit_config: dict = field(init=False)
    turbine_config: dict = field(init=False)
    floris_config: dict | None = field(init=False)
    orbit_hybrid_electrical_export_config: dict = field(init=False)
    design_scenario: dict = field(init=False)

    def __attrs_post_init__(self):
        (
            self.hopp_config,
            self.h2integrate_config,
            self.orbit_config,
            self.turbine_config,
            self.floris_config,
            self.orbit_hybrid_electrical_export_config,
        ) = he_util.get_inputs(
            self.filename_hopp_config,
            self.filename_h2integrate_config,
            filename_orbit_config=self.filename_orbit_config,
            filename_floris_config=self.filename_floris_config,
            filename_turbine_config=self.filename_turbine_config,
            verbose=self.verbose,
            show_plots=self.show_plots,
            save_plots=self.save_plots,
        )

        # n scenarios, n discrete variables
        self.design_scenario = self.h2integrate_config["plant_design"][
            f"scenario{self.plant_design_scenario}"
        ]
        self.design_scenario["id"] = self.plant_design_scenario

        # if design_scenario["h2_storage_location"] == "turbine":
        #     plant_config["h2_storage"]["type"] = "turbine"
        if "analysis_start_year" not in self.h2integrate_config["finance_parameters"]:
            analysis_start_year = self.h2integrate_config["project_parameters"]["atb_year"] + 2
            self.h2integrate_config["finance_parameters"].update(
                {"analysis_start_year": analysis_start_year}
            )

            msg = (
                "analysis_start_year not provided in h2integrate input file."
                f"Setting analysis_start_year to {analysis_start_year}."
            )
            warnings.warn(msg, UserWarning)

        if self.electrolyzer_rating_mw is not None:
            self.h2integrate_config["electrolyzer"]["flag"] = True
            self.h2integrate_config["electrolyzer"]["rating"] = self.electrolyzer_rating_mw

        if self.solar_rating is not None:
            self.hopp_config["site"]["solar"] = True
            self.hopp_config["technologies"]["pv"]["system_capacity_kw"] = self.solar_rating

        if self.battery_capacity_kw is not None:
            self.hopp_config["site"]["battery"]["flag"] = True
            self.hopp_config["technologies"]["battery"]["system_capacity_kw"] = (
                self.battery_capacity_kw
            )

        if self.battery_capacity_kwh is not None:
            self.hopp_config["site"]["battery"]["flag"] = True
            self.hopp_config["technologies"]["battery"]["system_capacity_kwh"] = (
                self.battery_capacity_kwh
            )

        if self.storage_type is not None:
            self.h2integrate_config["h2_storage"]["type"] = self.storage_type

        if self.wind_rating is not None:
            self.orbit_config["plant"]["capacity"] = int(self.wind_rating * 1e-3)
            self.orbit_config["plant"]["num_turbines"] = int(
                self.wind_rating * 1e-3 / self.turbine_config["turbine_rating"]
            )
            self.hopp_config["technologies"]["wind"]["num_turbines"] = self.orbit_config["plant"][
                "num_turbines"
            ]

        if self.grid_connection is not None:
            self.h2integrate_config["project_parameters"]["grid_connection"] = self.grid_connection
            if self.grid_connection:
                self.hopp_config["technologies"]["grid"]["interconnect_kw"] = (
                    self.orbit_config["plant"]["capacity"] * 1e6
                )


@define
class H2IntegrateSimulationOutput:
    """This is a dataclass to contain the outputs from H2Integrate

    Args:
        h2integrate_config (H2IntegrateSimulationConfig): all inputs to the h2integrate simulation
        hopp_interface (HoppInterface): the hopp interface created and used by H2Integrate in the
            simulation
        profast_lcoe (ProFAST): the profast instance used for the lcoe calculations
        profast_lcoh (ProFAST): the profast instance used for the lcoh calculations
        profast_lcoh (ProFAST): the profast instance used for the lcoh calculations if  hydrogen
            were produced only from the grid
        lcoe (float): levelized cost of energy (electricity)
        lcoh (float): levelized cost of hydrogen
        lcoh_grid_only (float): levelized cost of hydrogen if produced only from the grid
        hopp_results (dict): results from the hopp simulation
        electrolyzer_physics_results (dict): results of the electrolysis simulation
        capex_breakdown (dict): overnight capex broken down by technology
        opex_breakdown_annual (dict): annual operational expenditures broken down by technology
        annual_energy_breakdown (dict): annual energy generation and usage broken down by technology
        hourly_energy_breakdown (dict): hourly energy generation and usage broken down by technology
        remaining_power_profile (np.ndarray): unused power (hourly)
        steel_capacity (Optional[SteelCapacityModelOutputs]): steel capacity information
        steel_costs (Optional[SteelCostModelOutputs]): steel cost information
        steel_finance (Optional[SteelFinanceModelOutputs]): steel financial information
        iron_capacity (Optional[IronCapacityModelOutputs]): iron capacity information
        iron_costs (Optional[IronCostModelOutputs]): iron cost information
        iron_finance (Optional[IronFinanceModelOutputs]): iron financial information
        ammonia_capacity (Optional[AmmoniaCapacityModelOutputs]): ammonia capacity information
        ammonia_costs (Optional[AmmoniaCostModelOutputs]): ammonia cost information
        ammonia_finance (Optional[AmmoniaFinanceModelOutputs]): ammonia finance information
        platform_results (Optional[dict]): equipment platform information/outputs if used
    """

    # detailed simulation information
    h2integrate_config: H2IntegrateSimulationConfig
    hopp_interface: HoppInterface

    # detailed financial outputs
    profast_lcoe: ProFAST
    profast_lcoh: ProFAST
    profast_lcoh_grid_only: ProFAST
    profast_sol_lcoe: dict
    profast_sol_lcoh: dict
    profast_sol_lcoh_grid_only: dict

    # high-level results
    lcoe: float
    lcoh: float
    lcoh_grid_only: float

    # detailed output information
    hopp_results: dict
    electrolyzer_physics_results: dict
    capex_breakdown: dict
    opex_breakdown_annual: dict
    annual_energy_breakdown: dict
    hourly_energy_breakdown: dict
    remaining_power_profile: np.ndarray

    # optional outputs
    hopp_config: dict | None = field(default=None)
    h2_storage_max_fill_rate_kg_hr: dict | None = field(default=None)
    h2_storage_capacity_kg: dict | None = field(default=None)
    hydrogen_storage_state_of_charge_kg: dict | None = field(default=None)

    steel_capacity: SteelCapacityModelOutputs | None = field(default=None)
    steel_costs: SteelCostModelOutputs | None = field(default=None)
    steel_finance: SteelFinanceModelOutputs | None = field(default=None)

    iron_performance: IronPerformanceModelOutputs | None = field(default=None)
    iron_costs: IronCostModelOutputs | None = field(default=None)
    iron_finance: IronFinanceModelOutputs | None = field(default=None)

    ammonia_capacity: AmmoniaCapacityModelOutputs | None = field(default=None)
    ammonia_costs: AmmoniaCostModelOutputs | None = field(default=None)
    ammonia_finance: AmmoniaFinanceModelOutputs | None = field(default=None)

    platform_results: dict | None = field(default=None)

    def save_to_file(self, filename: str):
        """Saves select attributes of the class to a YAML file."""

        filepath = Path(filename)

        ignore = [
            "h2integrate_config",  # fails: max recursion depth
            "hopp_interface",  # fails: max recursion depth
            "hopp_results",  # fails: max recursion depth
            "profast_lcoe",  # fails: cannot pickle `dict_keys` object
            "profast_lcoh",  # fails: cannot pickle `dict_keys` object
            "profast_lcoh_grid_only",  # fails: cannot pickle `dict_keys` object
        ]

        # Convert the object to a dictionary of serializable types
        serialized_data = {}
        for attr in dir(self):
            # Avoid private attributes and methods
            if attr.startswith("_") or callable(getattr(self, attr)):
                continue
            if attr in ignore:
                continue
            try:
                value = getattr(self, attr)
                serialized_data[attr] = convert_to_serializable(value)
            except AttributeError:
                pass

        with filepath.open("w") as file:
            yaml.safe_dump(
                serialized_data, file, default_flow_style=False, allow_unicode=True, sort_keys=False
            )

    @classmethod
    def load_from_file(cls, filename: str) -> H2IntegrateSimulationOutput:
        """Creates an incomplete instance of H2IntegrateSimulationOutput from a previously saved
        `.yaml` file. The result is missing the following: `h2integrate_config`, `hopp_interface`,
        `profast_lcoe`, `profast_lcoh`, `profast_lcoh_grid_only`, and `hopp_results`. Note that
        data types will not exactly match the instance of H2IntegrateSimulationOutput that was
        saved due to required data type conversions for yaml output and easy loading.

        Args:
            filename (str): Path to the file where an instance of H2IntegrateSimulationOutput
            was saved

        Returns:
            (H2IntegrateSimulationOutput): An incomplete instance of H2IntegrateSimulationOutput.
        """

        def convert(value):
            """Recursively reconstruct complex types."""
            if isinstance(value, dict) and "__tuple__" in value:
                return tuple(convert(v) for v in value["items"])  # Reconstruct tuple
            if isinstance(value, list):
                return [convert(v) for v in value]
            elif isinstance(value, dict):
                # Heuristic for pandas DataFrame
                if all(isinstance(k, str) and isinstance(v, list) for k, v in value.items()):
                    return pd.DataFrame(value)
                elif all(
                    isinstance(k, str) and isinstance(v, (int, float, str))
                    for k, v in value.items()
                ):
                    return pd.Series(value)
                else:
                    return {k: convert(v) for k, v in value.items()}
            return value

        data = load_yaml(filename)

        kwargs = {f.name: convert(data.get(f.name)) for f in fields(cls)}
        return cls(**kwargs)


def setup_simulation(config: H2IntegrateSimulationConfig):
    """
    Sets up the simulation for H2Integrate.

    Configures various parameters for wind, PV, and battery technologies.
    This function ensures consistency between different configuration files,
    updates parameters as needed, and initializes the HOPP model.

    Args:
        config (H2IntegrateSimulationConfig): A configuration object containing
            all necessary parameters for the simulation, including design scenarios,
            ORBIT configurations, HOPP configurations, and H2Integrate-specific settings.

    Returns:
        tuple: A tuple containing:
            - config (H2IntegrateSimulationConfig): The updated configuration object.
            - hi: The initialized HOPP model.
            - wind_cost_results: Results from the wind cost model, or None if not applicable.

    Raises:
        UserWarning: Issues warnings when configuration mismatches are detected
        and corrected, or when default values are set for missing parameters.

    Notes:
        - For offshore wind scenarios, this function ensures consistency between
          ORBIT and H2Integrate configurations for parameters such as the number
          of turbines, site depth, turbine spacing, and row spacing.
        - Updates operation and maintenance (O&M) costs for wind, PV, and battery
          technologies based on the `cost_info` section of the HOPP configuration.
        - Initializes the HOPP model using the provided configurations and optionally
          saves physics results if specified in the configuration.
    """
    # run orbit for wind plant construction and other costs
    ## TODO get correct weather (wind, wave) inputs for ORBIT input (possibly via ERA5)
    if config.design_scenario["wind_location"] == "offshore":
        if (
            config.orbit_config["plant"]["num_turbines"]
            != config.hopp_config["technologies"]["wind"]["num_turbines"]
        ):
            config.orbit_config["plant"].update(
                {"num_turbines": config.hopp_config["technologies"]["wind"]["num_turbines"]}
            )
            msg = (
                f"'num_turbines' in the orbit_config was"
                f" {config.orbit_config['plant']['num_turbines']}, but 'num_turbines' in"
                f"hopp_config was"
                f" {config.hopp_config['technologies']['wind']['num_turbines']}. The "
                "'num_turbines' value in the orbit_config is being overwritten with the value"
                " from the hopp_config"
            )

            warnings.warn(msg, UserWarning)

        if config.orbit_config["site"]["depth"] != config.h2integrate_config["site"]["depth"]:
            config.orbit_config["site"].update(
                {"depth": config.h2integrate_config["site"]["depth"]}
            )
            msg = (
                f"site depth in the orbit_config was {config.orbit_config['site']['depth']}, "
                f"but site depth in"
                f" h2integrate_config was {config.h2integrate_config['site']['depth']}. The site"
                " depth value in the orbit_config is being overwritten with the value from"
                " the h2integrate_config."
            )
            warnings.warn(msg, UserWarning)

        if (
            config.orbit_config["plant"]["turbine_spacing"]
            != config.h2integrate_config["site"]["wind_layout"]["turbine_spacing"]
        ):
            config.orbit_config["plant"].update(
                {
                    "turbine_spacing": config.h2integrate_config["site"]["wind_layout"][
                        "turbine_spacing"
                    ]
                }
            )
            msg = (
                f"'turbine_spacing' in the orbit_config was"
                f" {config.orbit_config['plant']['turbine_spacing']}, but 'turbine_spacing' in"
                f" h2integrate_config was"
                f" {config.h2integrate_config['site']['wind_layout']['turbine_spacing']}. The"
                " 'turbine_spacing' value in the orbit_config is being overwritten with the "
                "value from the h2integrate_config"
            )
            warnings.warn(msg, UserWarning)

        if (
            config.orbit_config["plant"]["row_spacing"]
            != config.h2integrate_config["site"]["wind_layout"]["row_spacing"]
        ):
            config.orbit_config["plant"].update(
                {"row_spacing": config.h2integrate_config["site"]["wind_layout"]["row_spacing"]}
            )
            msg = (
                f"'row_spacing' in the orbit_config was"
                f" {config.orbit_config['plant']['row_spacing']}, but 'row_spacing' in"
                f" h2integrate_config was"
                f" {config.h2integrate_config['site']['wind_layout']['row_spacing']}. The"
                " 'row_spacing' value in the orbit_config is being overwritten with the value "
                "from the h2integrate_config"
            )
            warnings.warn(msg, UserWarning)

        wind_config = he_fin.WindCostConfig(
            design_scenario=config.design_scenario,
            hopp_config=config.hopp_config,
            h2integrate_config=config.h2integrate_config,
            orbit_config=config.orbit_config,
            orbit_hybrid_electrical_export_config=config.orbit_hybrid_electrical_export_config,
        )

        wind_cost_results = he_fin.run_wind_cost_model(
            wind_cost_inputs=wind_config, verbose=config.verbose
        )
        if "installation_time" not in config.h2integrate_config["project_parameters"].keys():
            config.h2integrate_config["project_parameters"].update(
                {"installation_time": wind_cost_results.installation_time}
            )
            msg = (
                "installation_time not provided in h2integrate input file."
                "Updating installation_time from Orbit results "
                f"({wind_cost_results.installation_time} months)."
            )
            warnings.warn(msg, UserWarning)
    else:
        wind_cost_results = None

    if "installation_time" not in config.h2integrate_config["project_parameters"].keys():
        config.h2integrate_config["project_parameters"].update({"installation_time": 0})
        msg = (
            "installation_time not provided in h2integrate input file."
            "Setting installation_time to 0 months."
        )
        warnings.warn(msg, UserWarning)
    # override individual fin_model values with cost_info values
    if "wind" in config.hopp_config["technologies"]:
        if ("wind_om_per_kw" in config.hopp_config["config"]["cost_info"]) and (
            config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_capacity"][
                0
            ]
            != config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
        ):
            for i in range(
                len(
                    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"][
                        "om_capacity"
                    ]
                )
            ):
                config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"][
                    "om_capacity"
                ][i] = config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]

                om_fixed_wind_fin_model = config.hopp_config["technologies"]["wind"]["fin_model"][
                    "system_costs"
                ]["om_capacity"][i]
                wind_om_per_kw = config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
                msg = (
                    f"'om_capacity[{i}]' in the wind 'fin_model' was {om_fixed_wind_fin_model},"
                    f" but 'wind_om_per_kw' in 'cost_info' was {wind_om_per_kw}. The "
                    "'om_capacity' value in the wind 'fin_model' is being overwritten with the "
                    "value from the 'cost_info'"
                )
                warnings.warn(msg, UserWarning)
        if ("wind_om_per_mwh" in config.hopp_config["config"]["cost_info"]) and (
            config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"][
                "om_production"
            ][0]
            != config.hopp_config["config"]["cost_info"]["wind_om_per_mwh"]
        ):
            # Use this to set the Production-based O&M amount [$/MWh]
            for i in range(
                len(
                    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"][
                        "om_production"
                    ]
                )
            ):
                config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"][
                    "om_production"
                ][i] = config.hopp_config["config"]["cost_info"]["wind_om_per_mwh"]
            om_wind_variable_cost = config.hopp_config["technologies"]["wind"]["fin_model"][
                "system_costs"
            ]["om_production"][i]
            wind_om_per_mwh = config.hopp_config["config"]["cost_info"]["wind_om_per_mwh"]
            msg = (
                f"'om_production' in the wind 'fin_model' was {om_wind_variable_cost}, but"
                f" 'wind_om_per_mwh' in 'cost_info' was {wind_om_per_mwh}. The 'om_production'"
                " value in the wind 'fin_model' is being overwritten with the value from the"
                " 'cost_info'"
            )
            warnings.warn(msg, UserWarning)

    if "pv" in config.hopp_config["technologies"]:
        if ("pv_om_per_kw" in config.hopp_config["config"]["cost_info"]) and (
            config.hopp_config["technologies"]["pv"]["fin_model"]["system_costs"]["om_capacity"][0]
            != config.hopp_config["config"]["cost_info"]["pv_om_per_kw"]
        ):
            for i in range(
                len(
                    config.hopp_config["technologies"]["pv"]["fin_model"]["system_costs"][
                        "om_capacity"
                    ]
                )
            ):
                config.hopp_config["technologies"]["pv"]["fin_model"]["system_costs"][
                    "om_capacity"
                ][i] = config.hopp_config["config"]["cost_info"]["pv_om_per_kw"]

                om_fixed_pv_fin_model = config.hopp_config["technologies"]["pv"]["fin_model"][
                    "system_costs"
                ]["om_capacity"][i]
                pv_om_per_kw = config.hopp_config["config"]["cost_info"]["pv_om_per_kw"]
                msg = (
                    f"'om_capacity[{i}]' in the pv 'fin_model' was {om_fixed_pv_fin_model}, "
                    f"but 'pv_om_per_kw' in 'cost_info' was {pv_om_per_kw}. The 'om_capacity'"
                    " value in the pv 'fin_model' is being overwritten with the value from"
                    " the 'cost_info'"
                )
                warnings.warn(msg, UserWarning)
        if ("pv_om_per_mwh" in config.hopp_config["config"]["cost_info"]) and (
            config.hopp_config["technologies"]["pv"]["fin_model"]["system_costs"]["om_production"][
                0
            ]
            != config.hopp_config["config"]["cost_info"]["pv_om_per_mwh"]
        ):
            # Use this to set the Production-based O&M amount [$/MWh]
            for i in range(
                len(
                    config.hopp_config["technologies"]["pv"]["fin_model"]["system_costs"][
                        "om_production"
                    ]
                )
            ):
                config.hopp_config["technologies"]["pv"]["fin_model"]["system_costs"][
                    "om_production"
                ][i] = config.hopp_config["config"]["cost_info"]["pv_om_per_mwh"]
            om_pv_variable_cost = config.hopp_config["technologies"]["pv"]["fin_model"][
                "system_costs"
            ]["om_production"][i]
            pv_om_per_mwh = config.hopp_config["config"]["cost_info"]["pv_om_per_mwh"]
            msg = (
                f"'om_production' in the pv 'fin_model' was {om_pv_variable_cost}, but"
                f" 'pv_om_per_mwh' in 'cost_info' was {pv_om_per_mwh}. The 'om_production'"
                " value in the pv 'fin_model' is being overwritten with the value from the"
                "'cost_info'"
            )
            warnings.warn(msg, UserWarning)

    if "battery" in config.hopp_config["technologies"]:
        if ("battery_om_per_kw" in config.hopp_config["config"]["cost_info"]) and (
            config.hopp_config["technologies"]["battery"]["fin_model"]["system_costs"][
                "om_capacity"
            ][0]
            != config.hopp_config["config"]["cost_info"]["battery_om_per_kw"]
        ):
            for i in range(
                len(
                    config.hopp_config["technologies"]["battery"]["fin_model"]["system_costs"][
                        "om_capacity"
                    ]
                )
            ):
                config.hopp_config["technologies"]["battery"]["fin_model"]["system_costs"][
                    "om_capacity"
                ][i] = config.hopp_config["config"]["cost_info"]["battery_om_per_kw"]

            om_batt_fixed_cost = config.hopp_config["technologies"]["battery"]["fin_model"][
                "system_costs"
            ]["om_capacity"][i]
            battery_om_per_kw = config.hopp_config["config"]["cost_info"]["battery_om_per_kw"]
            msg = (
                f"'om_capacity' in the battery 'fin_model' was {om_batt_fixed_cost}, but"
                f" 'battery_om_per_kw' in 'cost_info' was {battery_om_per_kw}. The"
                " 'om_capacity' value in the battery 'fin_model' is being overwritten with the"
                " value from the 'cost_info'"
            )
            warnings.warn(msg, UserWarning)
        if ("battery_om_per_mwh" in config.hopp_config["config"]["cost_info"]) and (
            config.hopp_config["technologies"]["battery"]["fin_model"]["system_costs"][
                "om_production"
            ][0]
            != config.hopp_config["config"]["cost_info"]["battery_om_per_mwh"]
        ):
            # Use this to set the Production-based O&M amount [$/MWh]
            for i in range(
                len(
                    config.hopp_config["technologies"]["battery"]["fin_model"]["system_costs"][
                        "om_production"
                    ]
                )
            ):
                config.hopp_config["technologies"]["battery"]["fin_model"]["system_costs"][
                    "om_production"
                ][i] = config.hopp_config["config"]["cost_info"]["battery_om_per_mwh"]
            om_batt_variable_cost = config.hopp_config["technologies"]["battery"]["fin_model"][
                "system_costs"
            ]["om_production"][i]
            battery_om_per_mwh = config.hopp_config["config"]["cost_info"]["battery_om_per_mwh"]
            msg = (
                f"'om_production' in the battery 'fin_model' was {om_batt_variable_cost}, but"
                f" 'battery_om_per_mwh' in 'cost_info' was {battery_om_per_mwh}. The"
                " 'om_production' value in the battery 'fin_model' is being overwritten with "
                "the value from the 'cost_info'",
            )
            warnings.warn(msg, UserWarning)

    # setup HOPP model
    hi = he_hopp.setup_hopp(
        config.hopp_config,
        config.h2integrate_config,
        config.orbit_config,
        config.turbine_config,
        config.floris_config,
        config.design_scenario,
        wind_cost_results,
        show_plots=config.show_plots,
        save_plots=config.save_plots,
    )

    if config.save_physics_results:
        gh_fio.save_physics_results_h2integrate_setup(config, wind_cost_results)

    return config, hi, wind_cost_results


def setup_simulation_for_iron(config: H2IntegrateSimulationConfig):
    """
    Sets up the simulation configuration for the iron model in the H2Integrate simulation.

    This function handles the initialization and configuration of the iron-related components
    in the simulation. Depending on whether the `iron_modular` flag is set, it either loads
    modular configurations for different stages of the iron model or a single configuration
    for the entire iron model. Additionally, it loads the physics setup for H2Integrate and
    ensures the `run_full_simulation` flag is reset to `False`. Useful for running only the
    iron model after saving off physics results from an earlier run.

    Args:
        config (H2IntegrateSimulationConfig): The simulation configuration object containing
            all necessary parameters and settings for the H2Integrate simulation.

    Returns:
        tuple: A tuple containing:
            - config (H2IntegrateSimulationConfig): The updated simulation configuration object.
            - hi (None): Placeholder for the HOPP Interface, which is not used in this function.
            - wind_cost_results: Results from the wind cost calculations during the physics setup.
    """
    # Only do the full setup (other than initialization) if running all of H2Integrate
    # If only running iron model, just load after initializing
    # Preserve iron from new instance of config
    if config.iron_modular:
        iron_ore_config = copy.deepcopy(config.h2integrate_config["iron_ore"])
        # iron_pre_config = copy.deepcopy(config.h2integrate_config['iron_pre'])
        iron_win_config = copy.deepcopy(config.h2integrate_config["iron_win"])
        iron_post_config = copy.deepcopy(config.h2integrate_config["iron_post"])
    else:
        iron_config = copy.deepcopy(config.h2integrate_config["iron"])

    # Identify the site resource
    config, wind_cost_results = gh_fio.load_physics_h2integrate_setup(config)

    # Flip run_full_simulation back to False (was True when saved)
    config.run_full_simulation = False
    if config.iron_modular:
        config.h2integrate_config["iron_ore"] = iron_ore_config
        # config.h2integrate_config['iron_pre'] = iron_pre_config
        config.h2integrate_config["iron_win"] = iron_win_config
        config.h2integrate_config["iron_post"] = iron_post_config
    else:
        config.h2integrate_config["iron"] = iron_config

    # HOPP Interface is expected as an output, but not needed
    hi = None

    return config, hi, wind_cost_results


def run_physics(config: H2IntegrateSimulationConfig, hi, wind_cost_results):
    """
    Executes the physics and financial models for the H2Integrate simulation.

    This function integrates various components of the H2Integrate simulation, including
    renewable energy generation, electrolyzer physics and cost modeling, desalination,
    hydrogen storage, transportation, and platform equipment. It also calculates the
    CapEx and OpEx for the system.

    Args:
        config (H2IntegrateSimulationConfig): Configuration object containing simulation
            parameters, design scenarios, and model configurations.
        hi: Hybrid interface object containing site-specific wind resource data and
            system configurations.
        wind_cost_results: Results from the wind cost model, used for financial calculations.

    Returns:
        tuple: A tuple containing the following results:
            - hopp_results (dict): Results from the HOPP model, including energy production data.
            - wind_annual_energy_kwh (float): Annual energy production from wind (kWh).
            - solar_pv_annual_energy_kwh (float): Annual energy production from solar PV (kWh).
            - wind_cost_results (dict): Results from the wind cost model.
            - electrolyzer_physics_results (dict): Results from the electrolyzer physics model.
            - electrolyzer_cost_results (dict): Results from the electrolyzer cost model.
            - desal_results (dict): Results from the desalination model.
            - h2_pipe_array_results (dict): Results from the hydrogen pipe array model.
            - h2_transport_compressor: Transport compressor object for hydrogen.
            - h2_transport_compressor_results (dict): Results from the hydrogen transport
                compressor model.
            - h2_transport_pipe_results (dict): Results from the hydrogen transport pipeline model.
            - pipe_storage: Storage object for hydrogen.
            - h2_storage_results (dict): Results from the hydrogen storage model.
            - total_accessory_power_renewable_kw (numpy.ndarray): Power consumption of accessory
                components powered by renewable energy (kW).
            - total_accessory_power_grid_kw (numpy.ndarray): Power consumption of accessory
                components powered by the grid (kW).
            - remaining_power_profile (numpy.ndarray): Remaining power profile available for
                electrolysis (kW).
            - capex (float): Total capital expenditure for the system.
            - capex_breakdown (dict): Breakdown of capital expenditure by component.
            - opex_annual (float): Annual operational expenditure for the system.
            - opex_breakdown_total (dict): Breakdown of operational expenditure
                (fixed and variable).
            - platform_results (dict): Results from the platform equipment model.
            - solver_results (tuple): Results from the energy solver for accessory components.

    Notes:
        - The function uses an internal solver to determine the energy availability for hydrogen
          production by accounting for non-electrolyzer energy consumption.
        - The function supports both onshore and offshore wind scenarios,
            with different configurations for hydrogen transportation and storage.
        - Plots of energy profiles can be generated and saved based on the configuration settings.
    """
    # run HOPP model
    hopp_results = he_hopp.run_hopp(
        hi,
        project_lifetime=config.h2integrate_config["project_parameters"]["project_lifetime"],
        verbose=config.verbose,
    )

    wind_annual_energy_kwh = hopp_results["annual_energies"][
        "wind"
    ]  # annual energy from wind (kWh)
    solar_pv_annual_energy_kwh = hopp_results["annual_energies"][
        "pv"
    ]  # annual energy from solar (kWh)

    if config.design_scenario["wind_location"] == "onshore":
        wind_config = he_fin.WindCostConfig(
            design_scenario=config.design_scenario,
            hopp_config=config.hopp_config,
            h2integrate_config=config.h2integrate_config,
            turbine_config=config.turbine_config,
            hopp_interface=hopp_results["hopp_interface"],
        )

        wind_cost_results = he_fin.run_wind_cost_model(
            wind_cost_inputs=wind_config, verbose=config.verbose
        )

    def energy_internals(
        hopp_results=hopp_results,
        wind_cost_results=wind_cost_results,
        design_scenario=config.design_scenario,
        orbit_config=config.orbit_config,
        hopp_config=config.hopp_config,
        h2integrate_config=config.h2integrate_config,
        turbine_config=config.turbine_config,
        wind_resource=hi.system.site.wind_resource,
        verbose=config.verbose,
        show_plots=config.show_plots,
        save_plots=config.save_plots,
        output_dir=config.output_dir,
        solver=True,
        power_for_peripherals_kw_in=0.0,
        breakdown=False,
    ):
        """
        Simulates the energy flow and cost analysis for a hybrid energy system.

        This portion of the system is inside a function so we can use a solver to determine the
        correct energy availability for h2 production.

        Args:
            hopp_results (dict): Results from the HOPP simulation, including power production data.
            wind_cost_results (dict): Cost results related to wind energy systems.
            design_scenario (dict): Configuration for the design scenario, including wind location
                and transportation type.
            orbit_config (dict): Configuration for ORBIT offshore wind modeling.
            hopp_config (dict): Configuration for HOPP simulation.
            h2integrate_config (dict): Configuration for the H2Integrate model.
            turbine_config (dict): Configuration for wind turbine parameters.
            wind_resource (object): Wind resource data for the site.
            verbose (bool): If True, prints detailed logs and results.
            show_plots (bool): If True, displays plots of energy profiles.
            save_plots (bool): If True, saves plots of energy profiles to the output directory.
            output_dir (str): Directory path to save output files and plots.
            solver (bool): If True, returns results for optimization solvers.
            power_for_peripherals_kw_in (float): Power allocated for peripheral systems in kW.
            breakdown (bool): If True and solver is True, returns a detailed breakdown of
                power usage.

        Returns:
            tuple or np.ndarray:
                - If `solver` is True and `breakdown` is True, returns a tuple containing:
                    - total_accessory_power_renewable_kw (np.ndarray): Renewable power used by
                        accessories.
                    - total_accessory_power_grid_kw (np.ndarray): Grid power used by accessories.
                    - desal_power_kw (np.ndarray): Power used for desalination in kW.
                    - h2_transport_compressor_power_kw (np.ndarray): Power used by the hydrogen
                        transport compressor in kW.
                    - h2_storage_power_kw (np.ndarray): Power used for hydrogen storage in kW.
                    - electrolyzer_energy_consumption_bop_kw (np.ndarray): Power used by
                        electrolyzer balance of plant in kW.
                    - remaining_power_profile (np.ndarray): Power available for electrolysis
                        after accessory usage.
                - If `solver` is True and `breakdown` is False, returns:
                    - total_accessory_power_renewable_kw (np.ndarray): Renewable power used
                        by accessories.
                - If `solver` is False, returns a tuple containing:
                    - electrolyzer_physics_results (dict): Results from the electrolyzer
                        physics model.
                    - electrolyzer_cost_results (dict): Results from the electrolyzer cost model.
                    - desal_results (dict): Results from the desalination model.
                    - h2_pipe_array_results (dict): Results from the hydrogen pipe array model.
                    - h2_transport_compressor (object): Hydrogen transport compressor object.
                    - h2_transport_compressor_results (dict): Results from the hydrogen
                        transport compressor model.
                    - h2_transport_pipe_results (dict): Results from the hydrogen transport
                        pipeline model.
                    - pipe_storage (object): Hydrogen storage pipe object.
                    - h2_storage_results (dict): Results from the hydrogen storage model.
                    - total_accessory_power_renewable_kw (np.ndarray): Renewable power used
                        by accessories.
                    - total_accessory_power_grid_kw (np.ndarray): Grid power used
                        by accessories.
                    - remaining_power_profile (np.ndarray): Power available for
                        electrolysis after accessory usage.
        """
        hopp_results_internal = dict(hopp_results)

        # set energy input profile
        ### subtract peripheral power from supply to get what is left for electrolyzer
        remaining_power_profile_in = np.zeros_like(
            hopp_results["combined_hybrid_power_production_hopp"]
        )

        high_count = sum(
            np.asarray(hopp_results["combined_hybrid_power_production_hopp"])
            >= power_for_peripherals_kw_in
        )
        total_peripheral_energy = power_for_peripherals_kw_in * 365 * 24
        distributed_peripheral_power = total_peripheral_energy / high_count

        remaining_power_profile_in = np.where(
            hopp_results["combined_hybrid_power_production_hopp"] - distributed_peripheral_power
            > 0,
            hopp_results["combined_hybrid_power_production_hopp"] - distributed_peripheral_power,
            0,
        )

        hopp_results_internal["combined_hybrid_power_production_hopp"] = tuple(
            remaining_power_profile_in
        )

        # run electrolyzer physics model
        electrolyzer_physics_results = he_elec.run_electrolyzer_physics(
            hopp_results_internal,
            config.h2integrate_config,
            wind_resource,
            design_scenario,
            show_plots=show_plots,
            save_plots=save_plots,
            output_dir=output_dir,
            verbose=verbose,
        )

        # run electrolyzer cost model
        electrolyzer_cost_results = he_elec.run_electrolyzer_cost(
            electrolyzer_physics_results,
            hopp_config,
            config.h2integrate_config,
            design_scenario,
            verbose=verbose,
        )

        # run electrolyzer bop model
        electrolyzer_energy_consumption_bop_kw = he_elec.run_electrolyzer_bop(
            h2integrate_config, electrolyzer_physics_results
        )

        desal_results = he_elec.run_desal(
            hopp_config, electrolyzer_physics_results, design_scenario, verbose
        )

        # run array system model
        h2_pipe_array_results = he_h2.run_h2_pipe_array(
            h2integrate_config,
            hopp_config,
            turbine_config,
            wind_cost_results,
            electrolyzer_physics_results,
            design_scenario,
            verbose,
        )

        # compressor #TODO size correctly
        (
            h2_transport_compressor,
            h2_transport_compressor_results,
        ) = he_h2.run_h2_transport_compressor(
            config.h2integrate_config,
            electrolyzer_physics_results,
            design_scenario,
            verbose=verbose,
        )

        # transport pipeline
        if design_scenario["wind_location"] == "offshore":
            h2_transport_pipe_results = he_h2.run_h2_transport_pipe(
                orbit_config,
                h2integrate_config,
                electrolyzer_physics_results,
                design_scenario,
                verbose=verbose,
            )
        if design_scenario["wind_location"] == "onshore":
            h2_transport_pipe_results = {
                "total capital cost [$]": [0 * 5433290.0184895478],
                "annual operating cost [$]": [0.0],
            }

        # pressure vessel storage
        pipe_storage, h2_storage_results = he_h2.run_h2_storage(
            hopp_config,
            h2integrate_config,
            turbine_config,
            electrolyzer_physics_results,
            design_scenario,
            verbose=verbose,
        )

        total_energy_available = np.sum(hopp_results["combined_hybrid_power_production_hopp"])

        ### get all energy non-electrolyzer usage in kw
        desal_power_kw = desal_results["power_for_desal_kw"]

        h2_transport_compressor_power_kw = h2_transport_compressor_results["compressor_power"]  # kW

        h2_storage_energy_kwh = h2_storage_results["storage_energy"]
        h2_storage_power_kw = h2_storage_energy_kwh * (1.0 / (365 * 24))

        total_accessory_power_renewable_kw = np.zeros(len(electrolyzer_energy_consumption_bop_kw))
        total_accessory_power_renewable_kw += electrolyzer_energy_consumption_bop_kw
        total_accessory_power_grid_kw = np.zeros(len(electrolyzer_energy_consumption_bop_kw))
        # if transport is not HVDC and h2 storage is on shore, then power the storage from
        # the grid
        if (design_scenario["transportation"] == "pipeline") and (
            design_scenario["h2_storage_location"] == "onshore"
        ):
            total_accessory_power_renewable_kw += desal_power_kw + h2_transport_compressor_power_kw
            total_accessory_power_grid_kw += h2_storage_power_kw
        else:
            total_accessory_power_renewable_kw += (
                desal_power_kw + h2_transport_compressor_power_kw + h2_storage_power_kw
            )

        ### subtract peripheral power from supply to get what is left for electrolyzer and
        # also get grid power
        remaining_power_profile = np.zeros_like(
            hopp_results["combined_hybrid_power_production_hopp"]
        )
        np.zeros_like(hopp_results["combined_hybrid_power_production_hopp"])
        remaining_power_profile = np.where(
            hopp_results["combined_hybrid_power_production_hopp"]
            - total_accessory_power_renewable_kw
            > 0,
            hopp_results["combined_hybrid_power_production_hopp"]
            - total_accessory_power_renewable_kw,
            0,
        )

        if verbose and not solver:
            print("\nEnergy/Power Results:")
            print("Supply (MWh): ", total_energy_available)
            print("Desal (kW): ", desal_power_kw)
            print("Transport compressor (kW): ", h2_transport_compressor_power_kw)
            print("Storage compression, refrigeration, etc (kW): ", h2_storage_power_kw)
            # print(
            #     "Difference: ",
            #     total_energy_available / (365 * 24)
            #     - np.sum(remaining_power_profile) / (365 * 24)
            #     - total_accessory_power_renewable_kw,
            # )

        if (show_plots or save_plots) and not solver:
            fig, ax = plt.subplots(1)
            plt.plot(
                np.asarray(hopp_results["combined_hybrid_power_production_hopp"]) * 1e-6,
                label="Total Energy Available",
            )
            plt.plot(
                remaining_power_profile * 1e-6,
                label="Energy Available for Electrolysis",
            )
            plt.xlabel("Hour")
            plt.ylabel("Power (GW)")
            plt.tight_layout()
            if save_plots:
                savepath = Path(config.output_dir).resolve() / "figures/power_series/"
                if not savepath.exists():
                    savepath.mkdir(parents=True)
                plt.savefig(savepath / f'power_{design_scenario["id"]}.png', transparent=True)
            if show_plots:
                plt.show()
        if solver:
            if breakdown:
                return (
                    total_accessory_power_renewable_kw,
                    total_accessory_power_grid_kw,
                    desal_power_kw,
                    h2_transport_compressor_power_kw,
                    h2_storage_power_kw,
                    electrolyzer_energy_consumption_bop_kw,
                    remaining_power_profile,
                )
            else:
                return total_accessory_power_renewable_kw
        else:
            return (
                electrolyzer_physics_results,
                electrolyzer_cost_results,
                desal_results,
                h2_pipe_array_results,
                h2_transport_compressor,
                h2_transport_compressor_results,
                h2_transport_pipe_results,
                pipe_storage,
                h2_storage_results,
                total_accessory_power_renewable_kw,
                total_accessory_power_grid_kw,
                remaining_power_profile,
            )

    # define function to provide to the brent solver
    def energy_residual_function(power_for_peripherals_kw_in):
        # get results for current design
        power_for_peripherals_kw_out = energy_internals(
            power_for_peripherals_kw_in=power_for_peripherals_kw_in,
            solver=True,
            verbose=False,
        )

        # collect residual
        power_residual = power_for_peripherals_kw_out - power_for_peripherals_kw_in

        return power_residual

    def simple_solver(initial_guess=0.0):
        # get results for current design
        (
            total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw,
            desal_power_kw,
            h2_transport_compressor_power_kw,
            h2_storage_power_kw,
            electrolyzer_bop_kw,
            remaining_power_profile,
        ) = energy_internals(
            power_for_peripherals_kw_in=initial_guess,
            solver=True,
            verbose=False,
            breakdown=True,
        )

        return (
            total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw,
            desal_power_kw,
            h2_transport_compressor_power_kw,
            h2_storage_power_kw,
            electrolyzer_bop_kw,
        )

    ############# solving for energy needed for non-electrolyzer components ##################
    # this approach either exactly over over-estimates the energy needed for non-electrolyzer
    # components
    solver_results = simple_solver(0)
    solver_result = solver_results[0]

    # # this is a check on the simple solver
    # print("\nsolver result: ", solver_result)
    # residual = energy_residual_function(solver_result)
    # print("\nresidual: ", residual)

    # this approach exactly sizes the energy needed for the non-electrolyzer components
    # (according to the current models anyway)
    # solver_result = optimize.brentq(energy_residual_function, -10, 20000, rtol=1E-5)
    # OptimizeResult = optimize.root(energy_residual_function, 11E3, tol=1)
    # solver_result = OptimizeResult.x
    # solver_results = simple_solver(solver_result)
    # solver_result = solver_results[0]
    # print(solver_result)

    ##########################################################################################

    # get results for final design
    (
        electrolyzer_physics_results,
        electrolyzer_cost_results,
        desal_results,
        h2_pipe_array_results,
        h2_transport_compressor,
        h2_transport_compressor_results,
        h2_transport_pipe_results,
        pipe_storage,
        h2_storage_results,
        total_accessory_power_renewable_kw,
        total_accessory_power_grid_kw,
        remaining_power_profile,
    ) = energy_internals(solver=False, power_for_peripherals_kw_in=solver_result)

    ## end solver loop here
    platform_results = he_h2.run_equipment_platform(
        config.hopp_config,
        config.h2integrate_config,
        config.orbit_config,
        config.design_scenario,
        hopp_results,
        electrolyzer_physics_results,
        h2_storage_results,
        desal_results,
        verbose=config.verbose,
    )

    ################# OSW intermediate calculations aka final financial calculations

    # TODO double check full-system CAPEX
    capex, capex_breakdown = he_fin.run_capex(
        hopp_results,
        wind_cost_results,
        electrolyzer_cost_results,
        h2_pipe_array_results,
        h2_transport_compressor_results,
        h2_transport_pipe_results,
        h2_storage_results,
        config.hopp_config,
        config.h2integrate_config,
        config.design_scenario,
        desal_results,
        platform_results,
        verbose=config.verbose,
    )

    # TODO double check full-system OPEX
    opex_annual, opex_breakdown_annual = he_fin.run_fixed_opex(
        hopp_results,
        wind_cost_results,
        electrolyzer_cost_results,
        h2_pipe_array_results,
        h2_transport_compressor_results,
        h2_transport_pipe_results,
        h2_storage_results,
        config.hopp_config,
        config.h2integrate_config,
        desal_results,
        platform_results,
        verbose=config.verbose,
        total_export_system_cost=capex_breakdown["electrical_export_system"],
    )

    vopex_breakdown_annual = he_fin.run_variable_opex(
        electrolyzer_cost_results, config.h2integrate_config
    )

    opex_breakdown_total = {
        "fixed_om": opex_breakdown_annual,
        "variable_om": vopex_breakdown_annual,
    }

    if config.verbose:
        print(
            "hybrid plant capacity factor: ",
            np.sum(hopp_results["combined_hybrid_power_production_hopp"])
            / (hopp_results["hybrid_plant"].system_capacity_kw.hybrid * 365 * 24),
        )

    return (
        hopp_results,
        wind_annual_energy_kwh,
        solar_pv_annual_energy_kwh,
        wind_cost_results,
        electrolyzer_physics_results,
        electrolyzer_cost_results,
        desal_results,
        h2_pipe_array_results,
        h2_transport_compressor,
        h2_transport_compressor_results,
        h2_transport_pipe_results,
        pipe_storage,
        h2_storage_results,
        total_accessory_power_renewable_kw,
        total_accessory_power_grid_kw,
        remaining_power_profile,
        capex,
        capex_breakdown,
        opex_annual,
        opex_breakdown_total,
        platform_results,
        solver_results,
    )


def run_financials(
    config,
    hopp_results,
    wind_cost_results,
    electrolyzer_physics_results,
    capex_breakdown,
    opex_breakdown_total,
    total_accessory_power_renewable_kw,
    total_accessory_power_grid_kw,
    wind_annual_energy_kwh,
    solar_pv_annual_energy_kwh,
):
    """
    Runs financial analysis for the H2Integrate simulation.

    This financial analysis includes calculations for LCOE and LCOH
    under various scenarios.

    Args:
        config (object): Configuration object containing simulation parameters,
            financial settings, and output options.
        hopp_results (dict): Results from the HOPP simulation, including energy
            production and system performance metrics.
        wind_cost_results (dict): Cost breakdown for the wind energy system.
        electrolyzer_physics_results (dict): Results from the electrolyzer physics
            simulation, including hydrogen production and power consumption.
        capex_breakdown (dict): Capital expenditure breakdown for the project.
        opex_breakdown_total (dict): Total operational expenditure breakdown, including
            fixed and variable costs.
        total_accessory_power_renewable_kw (float): Total accessory power consumption
            supplied by renewable energy sources in kilowatts.
        total_accessory_power_grid_kw (float): Total accessory power consumption
            supplied by the grid in kilowatts.
        wind_annual_energy_kwh (float): Annual energy production from wind in kilowatt-hours.
        solar_pv_annual_energy_kwh (float): Annual energy production from solar PV in
            kilowatt-hours.

    Returns:
        tuple: A tuple containing the following:
            - lcoe (float): Levelized Cost of Energy for the system.
            - pf_lcoe (float): ProFAST LCOE results.
            - sol_lcoe (float): Solved LCOE results.
            - lcoh (float): Levelized Cost of Hydrogen for the full plant model.
            - pf_lcoh (float): ProFAST LCOH results.
            - sol_lcoh (float): Solved LCOH results.
            - lcoh_grid_only (float): LCOH for grid-only operation.
            - pf_grid_only (float): ProFAST grid-only results.
            - sol_grid_only (float): Solved grid-only results.
            - hydrogen_annual_energy_kwh (float): Annual energy consumption for hydrogen
              production in kilowatt-hours.
            - hydrogen_amount_kgpy (float): Annual hydrogen production in kilograms per year.
    """
    opex_breakdown_annual = opex_breakdown_total["fixed_om"]
    lcoe, pf_lcoe, sol_lcoe = he_fin.run_profast_lcoe(
        config.h2integrate_config,
        wind_cost_results,
        capex_breakdown,
        opex_breakdown_annual,
        hopp_results,
        config.incentive_option,
        config.design_scenario,
        verbose=config.verbose,
        show_plots=config.show_plots,
        save_plots=config.save_plots,
        output_dir=config.output_dir,
    )
    electrolyzer_performance_results = ElectrolyzerLCOHInputConfig(
        electrolyzer_physics_results=electrolyzer_physics_results,
        electrolyzer_config=config.h2integrate_config["electrolyzer"],
        analysis_start_year=config.h2integrate_config["finance_parameters"]["analysis_start_year"],
        installation_period_months=config.h2integrate_config["project_parameters"][
            "installation_time"
        ],
    )
    lcoh_grid_only, pf_grid_only, sol_grid_only = he_fin.run_profast_grid_only(
        config.h2integrate_config,
        wind_cost_results,
        electrolyzer_performance_results,
        capex_breakdown,
        opex_breakdown_total,
        hopp_results,
        config.design_scenario,
        total_accessory_power_renewable_kw,
        total_accessory_power_grid_kw,
        verbose=config.verbose,
        show_plots=config.show_plots,
        save_plots=config.save_plots,
        output_dir=config.output_dir,
    )
    lcoh, pf_lcoh, sol_lcoh = he_fin.run_profast_full_plant_model(
        config.h2integrate_config,
        wind_cost_results,
        electrolyzer_performance_results,
        capex_breakdown,
        opex_breakdown_total,
        hopp_results,
        config.incentive_option,
        config.design_scenario,
        total_accessory_power_renewable_kw,
        total_accessory_power_grid_kw,
        verbose=config.verbose,
        show_plots=config.show_plots,
        save_plots=config.save_plots,
        output_dir=config.output_dir,
    )

    # save lcoh, lcoe and electrolyzer physics results
    if config.save_physics_results:
        gh_fio.save_physics_results_h2integrate_simulation(
            config,
            lcoh,
            lcoe,
            electrolyzer_physics_results,
            wind_annual_energy_kwh,
            solar_pv_annual_energy_kwh,
            0,
        )
    hydrogen_amount_kgpy = electrolyzer_physics_results["H2_Results"][
        "Life: Annual H2 production [kg/year]"
    ]

    hydrogen_annual_energy_kwh = electrolyzer_physics_results["power_to_electrolyzer_kw"]

    return (
        lcoe,
        pf_lcoe,
        sol_lcoe,
        lcoh,
        pf_lcoh,
        sol_lcoh,
        lcoh_grid_only,
        pf_grid_only,
        sol_grid_only,
        hydrogen_annual_energy_kwh,
        hydrogen_amount_kgpy,
    )


def run_simulation(config: H2IntegrateSimulationConfig):
    """
    Executes the H2Integrate simulation based on the provided configuration.

    This function performs simulations to model the integration of
    renewable energy sources, hydrogen production, and
    downstream applications such as steel, iron, and ammonia production. It
    supports multiple levels of output detail and can optionally perform
    post-processing and life cycle analysis (LCA).

    Args:
        config (H2IntegrateSimulationConfig): Configuration object containing
            all necessary parameters for the simulation, including user inputs,
            simulation settings, and output preferences.

    Returns:
        Union[int, float, tuple, H2IntegrateSimulationOutput, list]:
            The output depends on the `config.output_level`:
            - 0: Returns 0.
            - 1: Returns the levelized cost of hydrogen (LCOH).
            - 2: Returns a tuple containing LCOH, levelized cost of energy (LCOE),
              CAPEX breakdown, annual OPEX breakdown, profast LCOH, and electrolyzer
              physics results.
            - 3: Returns a tuple containing LCOH, LCOE, CAPEX breakdown, annual
              OPEX breakdown, profast LCOH, electrolyzer physics results, profast
              LCOE, and annual energy breakdown.
            - 4: Returns a tuple containing LCOE, LCOH, and LCOH with grid-only
              energy.
            - 5: Returns a tuple containing LCOE, LCOH, LCOH with grid-only energy,
              and HOPP results.
            - 6: Returns a tuple containing HOPP results, electrolyzer physics
              results, and the remaining power profile.
            - 7: Returns a tuple containing LCOE, LCOH, and financial results for
              iron and ammonia (or steel and ammonia if iron is not configured).
            - 8: Returns an `H2IntegrateSimulationOutput` object containing detailed
              simulation results.
            - 9: Returns a list containing LCOE, LCOH, iron finance, and iron post
              finance.

    Raises:
        NotImplementedError: If the capacity denominator for the iron model is
            set to "steel" without a suitable configuration.
        ValueError: If invalid product selections are provided for the iron or
            ammonia modules.

    Notes:
        - The function supports modular configurations for iron production,
          allowing separate modeling of ore, pre-reduction, reduction, and
          post-reduction stages.
        - If `config.use_profast` is enabled, financial analysis is performed
          using the ProFAST tool.
        - Post-processing and LCA calculations are optional and can be enabled
          via the configuration.
        - Outputs can be saved to files if specified in the configuration.
    """
    if config.user_lcoe is not None and config.user_lcoh is not None:
        lcoe = float(config.user_lcoe)
        lcoh = float(config.user_lcoh)
        wind_annual_energy_kwh = float(config.user_annual_wind_kwh_prod)
        solar_pv_annual_energy_kwh = float(config.user_annual_pv_kwh_prod)
        hydrogen_annual_energy_kwh = float(config.user_life_annual_h2_kwh)
        hydrogen_amount_kgpy = float(config.user_life_annual_h2_prod)
        config.run_full_simulation = False
    else:
        if config.run_full_simulation:
            config, hi, wind_cost_results = setup_simulation(config=config)
        else:
            setup_simulation_for_iron(config=config)

    # Only run the "pre-iron" steps if needed
    # Otherwise, load their outputs from pickles
    if config.run_full_simulation:
        physics_results = run_physics(config, hi, wind_cost_results)

        (
            hopp_results,
            wind_annual_energy_kwh,
            solar_pv_annual_energy_kwh,
            wind_cost_results,
            electrolyzer_physics_results,
            electrolyzer_cost_results,
            desal_results,
            h2_pipe_array_results,
            h2_transport_compressor,
            h2_transport_compressor_results,
            h2_transport_pipe_results,
            pipe_storage,
            h2_storage_results,
            total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw,
            remaining_power_profile,
            capex,
            capex_breakdown,
            opex_annual,
            opex_breakdown_total,
            platform_results,
            solver_results,
        ) = physics_results
        opex_breakdown_annual = opex_breakdown_total["fixed_om"]

    steel_finance = None
    iron_finance = None
    ammonia_finance = None

    if config.use_profast:
        if config.run_full_simulation:
            (
                lcoe,
                pf_lcoe,
                sol_lcoe,
                lcoh,
                pf_lcoh,
                sol_lcoh,
                lcoh_grid_only,
                pf_grid_only,
                sol_grid_only,
                hydrogen_annual_energy_kwh,
                hydrogen_amount_kgpy,
            ) = run_financials(
                config,
                hopp_results,
                wind_cost_results,
                electrolyzer_physics_results,
                capex_breakdown,
                opex_breakdown_total,
                total_accessory_power_renewable_kw,
                total_accessory_power_grid_kw,
                wind_annual_energy_kwh,
                solar_pv_annual_energy_kwh,
            )
        else:
            if config.user_lcoe is None and config.user_lcoh is None:
                # load lcoh, lcoe and electrolyzer physics results from previous run
                (
                    lcoh,
                    lcoe,
                    electrolyzer_physics_results,
                    wind_annual_energy_kwh,
                    solar_pv_annual_energy_kwh,
                ) = gh_fio.load_physics_h2integrate_simulation(config)
                hydrogen_amount_kgpy = electrolyzer_physics_results["H2_Results"][
                    "Life: Annual H2 production [kg/year]"
                ]

                hydrogen_annual_energy_kwh = electrolyzer_physics_results[
                    "power_to_electrolyzer_kw"
                ]

        if "steel" in config.h2integrate_config:
            steel_config = copy.deepcopy(config.h2integrate_config)
            if config.verbose:
                print("Running steel\n")

            # use lcoh from the electrolyzer model if it is not already in the config
            if "lcoh" not in steel_config["steel"]["finances"]:
                steel_config["steel"]["finances"]["lcoh"] = lcoh

            # use lcoh from the electrolyzer model if it is not already in the config
            if "lcoh" not in steel_config["steel"]["costs"]:
                steel_config["steel"]["costs"]["lcoh"] = lcoh

            # use the hydrogen amount from the electrolyzer physics model if it is not already in
            # the config
            if "hydrogen_amount_kgpy" not in steel_config["steel"]["capacity"]:
                steel_config["steel"]["capacity"]["hydrogen_amount_kgpy"] = hydrogen_amount_kgpy

            steel_capacity, steel_costs, steel_finance = run_steel_full_model(
                steel_config,
                save_plots=config.save_plots,
                show_plots=config.show_plots,
                output_dir=config.output_dir,
                design_scenario_id=config.design_scenario["id"],
            )

        if any(
            i in config.h2integrate_config for i in ["iron", "iron_pre", "iron_win", "iron_post"]
        ):
            config.h2integrate_config["iron_out_fn"] = config.iron_out_fn
            iron_config = copy.deepcopy(config.h2integrate_config)
            cap_denom = iron_config["iron_win"]["performance"]["capacity_denominator"]
            # Check that steel is not being specified as capacity denominator
            # without a suitable configuration (e.g. EAF)
            if cap_denom == "steel":
                raise NotImplementedError("Haven't set up to calculate per unit steel yet")
                # if "eaf" not in iron_config["iron_post"]["product selection"]:
                #     msg = (
                #         "Steel was chosen for capacity denominator, but"
                #         " the iron model is not set up produce steel!"
                #         " (try adding an EAF to the iron_post module)"
                #     )
                #     raise ValueError(msg)
            if config.verbose:
                print("Running iron\n")

            if not config.iron_modular:
                # use lcoh from the electrolyzer model if it is not already in the config
                if "lcoh" not in iron_config["iron"]["finances"]:
                    iron_config["iron"]["finances"]["lcoh"] = lcoh

                # use lcoh from the electrolyzer model if it is not already in the config
                if "lcoh" not in iron_config["iron"]["costs"]:
                    iron_config["iron"]["costs"]["lcoh"] = lcoh

                # use the hydrogen amount from the electrolyzer physics model if it is not
                # already in the config
                if "hydrogen_amount_kgpy" not in iron_config["iron"]["performance"]:
                    iron_config["iron"]["performance"]["hydrogen_amount_kgpy"] = (
                        hydrogen_amount_kgpy
                    )

                iron_performance, iron_costs, iron_finance = run_iron_full_model(iron_config)

            else:
                # This is not the most graceful way to do this... but it avoids copied imports
                # and copying iron.py
                iron_ore_config = copy.deepcopy(iron_config)
                copy.deepcopy(iron_config)
                iron_win_config = copy.deepcopy(iron_config)
                iron_post_config = copy.deepcopy(iron_config)
                iron_ore_config["iron"] = iron_config["iron_ore"]
                # iron_pre_config["iron"] = iron_config["iron_pre"]
                iron_win_config["iron"] = iron_config["iron_win"]
                iron_post_config["iron"] = iron_config["iron_post"]
                for sub_iron_config in [
                    iron_ore_config,
                    iron_win_config,
                    iron_post_config,
                ]:  # ,iron_post_config]: # iron_pre_config, iron_post_config
                    sub_iron_config["iron"]["performance"]["hydrogen_amount_kgpy"] = (
                        hydrogen_amount_kgpy
                    )
                    sub_iron_config["iron"]["costs"]["lcoe"] = lcoe
                    sub_iron_config["iron"]["finances"]["lcoe"] = lcoe
                    sub_iron_config["iron"]["costs"]["lcoh"] = lcoh
                    sub_iron_config["iron"]["finances"]["lcoh"] = lcoh

                # TODO: find a way of looping the above and below
                iron_ore_performance, iron_ore_costs, iron_ore_finance = run_iron_full_model(
                    iron_ore_config
                )

                # TODO: save all the individual module outputs, using a loop
                # Identify the site

                gh_fio.save_iron_ore_results(
                    config, iron_ore_config, iron_ore_performance, iron_ore_costs, iron_ore_finance
                )

                # iron_pre_performance, iron_pre_costs, iron_pre_finance = \
                #     run_iron_full_model(iron_pre_config)

                iron_transport_cost_tonne, ore_profit_pct = calc_iron_ship_cost(iron_win_config)

                ### DRI ----------------------------------------------------------------------------
                if iron_win_config["iron"]["product_selection"] not in ["ng_dri", "h2_dri"]:
                    raise ValueError(
                        "The product selection for the iron win module must be either \
                        'ng_dri' or 'h2_dri'"
                    )

                iron_win_config["iron"]["finances"]["ore_profit_pct"] = ore_profit_pct
                iron_win_config["iron"]["costs"]["iron_transport_tonne"] = iron_transport_cost_tonne
                iron_win_config["iron"]["costs"]["lco_iron_ore_tonne"] = iron_ore_finance.sol["lco"]
                iron_win_performance, iron_win_costs, iron_win_finance = run_iron_full_model(
                    iron_win_config
                )

                ### EAF ----------------------------------------------------------------------------
                if iron_config["iron_post"]["product_selection"] == "none":
                    iron_performance = iron_win_performance
                    iron_costs = iron_win_costs
                    iron_finance = iron_win_finance

                else:
                    if iron_post_config["iron"]["product_selection"] not in ["ng_eaf", "h2_eaf"]:
                        raise ValueError(
                            "The product selection for the iron post module must be either \
                            'ng_eaf' or 'h2_eaf'"
                        )
                    pf_config = rev_pf_tools.make_pf_config_from_profast(
                        iron_win_finance.pf
                    )  # dictionary of profast objects
                    pf_dict = rev_pf_tools.convert_pf_res_to_pf_config(
                        copy.deepcopy(pf_config)
                    )  # profast dictionary of values
                    iron_post_config["iron"]["finances"]["pf"] = pf_dict
                    iron_post_config["iron"]["costs"]["lco_iron_ore_tonne"] = iron_ore_finance.sol[
                        "lco"
                    ]
                    iron_post_config["iron"]["performance"]["capacity_denominator"] = cap_denom
                    iron_post_performance, iron_post_costs, iron_post_finance = run_iron_full_model(
                        iron_post_config
                    )

                    iron_performance = iron_post_performance
                    iron_costs = iron_post_costs
                    iron_finance = iron_post_finance
        else:
            iron_finance = {}

        if "ammonia" in config.h2integrate_config:
            ammonia_config = copy.deepcopy(config.h2integrate_config)
            if config.verbose:
                print("Running ammonia\n")

            if "hydrogen_cost" not in ammonia_config["ammonia"]["costs"]["feedstocks"]:
                ammonia_config["ammonia"]["costs"]["feedstocks"]["hydrogen_cost"] = lcoh

            # use the hydrogen amount from the electrolyzer physics model if it is not already in
            # the config
            if "hydrogen_amount_kgpy" not in ammonia_config["ammonia"]["capacity"]:
                ammonia_config["ammonia"]["capacity"]["hydrogen_amount_kgpy"] = hydrogen_amount_kgpy

            ammonia_capacity, ammonia_costs, ammonia_finance = run_ammonia_full_model(
                ammonia_config,
                save_plots=config.save_plots,
                show_plots=config.show_plots,
                output_dir=config.output_dir,
                design_scenario_id=config.design_scenario["id"],
            )

        else:
            ammonia_finance = {}

    ################# end OSW intermediate calculations
    if config.post_processing:
        annual_energy_breakdown, hourly_energy_breakdown = he_util.post_process_simulation(
            lcoe,
            lcoh,
            pf_lcoh,
            pf_lcoe,
            hopp_results,
            electrolyzer_physics_results,
            config.hopp_config,
            config.h2integrate_config,
            config.orbit_config,
            config.turbine_config,
            h2_storage_results,
            total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw,
            capex_breakdown,
            opex_breakdown_annual,
            wind_cost_results,
            platform_results,
            desal_results,
            config.design_scenario,
            config.plant_design_scenario,
            config.incentive_option,
            solver_results=solver_results,
            show_plots=config.show_plots,
            save_plots=config.save_plots,
            verbose=config.verbose,
            output_dir=config.output_dir,
        )  # , lcoe, lcoh, lcoh_with_grid, lcoh_grid_only)
    # For iron model - save outputs and run LCA outside of post-processing step
    if any(i in config.h2integrate_config for i in ["iron", "iron_pre", "iron_win", "iron_post"]):
        gh_fio.save_iron_results(config, iron_performance, iron_costs, iron_finance)
        if iron_config["lca_config"]["run_lca"]:
            lca_df = calculate_lca(
                wind_annual_energy_kwh=wind_annual_energy_kwh,
                solar_pv_annual_energy_kwh=solar_pv_annual_energy_kwh,
                energy_shortfall_hopp=0,
                h2_annual_prod_kg=hydrogen_amount_kgpy,
                energy_to_electrolyzer_kwh=hydrogen_annual_energy_kwh,
                hopp_config=config.hopp_config,
                h2integrate_config=config.h2integrate_config,
                total_accessory_power_renewable_kw=0,
                total_accessory_power_grid_kw=0,
                plant_design_scenario_number=9,
                incentive_option_number=1,
            )

    # return
    if config.output_level == 0:
        return 0
    elif config.output_level == 1:
        return lcoh
    elif config.output_level == 2:
        return (
            lcoh,
            lcoe,
            capex_breakdown,
            opex_breakdown_annual,
            pf_lcoh,
            electrolyzer_physics_results,
        )
    elif config.output_level == 3:
        return (
            lcoh,
            lcoe,
            capex_breakdown,
            opex_breakdown_annual,
            pf_lcoh,
            electrolyzer_physics_results,
            pf_lcoe,
            annual_energy_breakdown,
        )
    elif config.output_level == 4:
        return lcoe, lcoh, lcoh_grid_only
    elif config.output_level == 5:
        return lcoe, lcoh, lcoh_grid_only, hopp_results["hopp_interface"]
    elif config.output_level == 6:
        return hopp_results, electrolyzer_physics_results, remaining_power_profile

    elif config.output_level == 7:
        if any(
            i in config.h2integrate_config
            for i in ["iron", "iron_pre", "iron_pre", "iron_win", "iron_post"]
        ):
            if "ng" in iron_config["iron_win"]["product_selection"]:
                LCA_label = "NG DRI Total Lifetime Average GHG Emissions (kg-CO2e/MT steel)"
            elif "h2" in iron_config["iron_win"]["product_selection"]:
                LCA_label = (
                    "H2 DRI Electrolysis Total Lifetime Average GHG Emissions (kg-CO2e/MT steel)"
                )
            if iron_config["lca_config"]["run_lca"]:
                gh_fio.save_iron_results(
                    config, iron_performance, iron_costs, iron_finance, lca_df[LCA_label].values[0]
                )
                ammonia_finance = lca_df[LCA_label].values[
                    0
                ]  # repurposing ammonia finance to hold CI
            return lcoe, lcoh, iron_finance, ammonia_finance
        else:
            return lcoe, lcoh, steel_finance, ammonia_finance
    elif config.output_level == 8:
        output = H2IntegrateSimulationOutput(
            config,
            hi,
            pf_lcoe,
            pf_lcoh,
            pf_grid_only,
            sol_lcoe,
            sol_lcoh,
            sol_grid_only,
            lcoe,
            lcoh,
            lcoh_grid_only,
            hopp_results,
            electrolyzer_physics_results,
            capex_breakdown,
            opex_breakdown_annual,
            annual_energy_breakdown,
            hourly_energy_breakdown,
            remaining_power_profile,
            h2_storage_max_fill_rate_kg_hr=(
                None
                if "h2_storage_max_fill_rate_kg_hr" not in h2_storage_results
                else h2_storage_results["h2_storage_max_fill_rate_kg_hr"]
            ),
            h2_storage_capacity_kg=(
                None
                if "h2_storage_capacity_kg" not in h2_storage_results
                else h2_storage_results["h2_storage_capacity_kg"]
            ),
            hydrogen_storage_state_of_charge_kg=(
                None
                if "hydrogen_storage_soc" not in h2_storage_results
                else h2_storage_results["hydrogen_storage_soc"]
            ),
            steel_capacity=(None if "steel" not in config.h2integrate_config else steel_capacity),
            steel_costs=(None if "steel" not in config.h2integrate_config else steel_costs),
            steel_finance=(None if "steel" not in config.h2integrate_config else steel_finance),
            ammonia_capacity=(
                None if "ammonia" not in config.h2integrate_config else ammonia_capacity
            ),
            ammonia_costs=(None if "ammonia" not in config.h2integrate_config else ammonia_costs),
            ammonia_finance=(
                None if "ammonia" not in config.h2integrate_config else ammonia_finance
            ),
            platform_results=platform_results,
        )
        return output
    elif config.output_level == 9:
        return [lcoe, lcoh, iron_finance, iron_post_finance]

        if config.save_h2integrate_output:
            output.save_to_file(Path(config.output_dir).resolve() / "data/h2integrate_output.yaml")

        return output


def run_sweeps(
    simulate=False,
    verbose=True,
    show_plots=True,
    use_profast=True,
    output_dir="output/",
):
    """
    Executes simulation sweeps and optionally generates plots for analyzing
    LCOH as a function of electrolyzer and wind plant ratings under various
    storage configurations.

    Args:
        simulate (bool, optional):
            If True, runs simulations and saves results to files.
            Disables verbose output and plotting. Defaults to False.
        verbose (bool, optional):
            If True, enables detailed output during simulations.
            Ignored if `simulate` is True. Defaults to True.
        show_plots (bool, optional):
            If True, generates and displays plots of LCOH vs.
            electrolyzer/wind plant rating ratio. Defaults to True.
        use_profast (bool, optional):
            If True, uses the PROFast tool for cost analysis during
            simulations. Defaults to True.
        output_dir (str, optional):
            Directory where simulation results and plots are saved.
            Defaults to "output/".

    Notes:
        - When `simulate` is True, the function performs simulations for
          different wind plant ratings and storage types, saving the
          results to text files in the specified `output_dir`.
        - When `show_plots` is True, the function reads precomputed data
          files and generates plots comparing LCOH for different storage
          configurations and wind plant ratings.
        - The plots include annotations for the optimal electrolyzer/wind
          plant rating ratio that minimizes LCOH.

    Example:
        To run simulations and save results:
        >>> run_sweeps(simulate=True, output_dir="results/")
        To generate plots from precomputed data:
        >>> run_sweeps(show_plots=True, output_dir="results/")
    """
    if simulate:
        verbose = False
        show_plots = False
    if simulate:
        storage_types = ["none", "pressure_vessel", "pipe", "salt_cavern"]
        wind_ratings = [400]  # , 800, 1200] #[200, 400, 600, 800]

        for wind_rating in wind_ratings:
            ratings = np.linspace(round(0.2 * wind_rating, ndigits=0), 2 * wind_rating + 1, 50)
            for storage_type in storage_types:
                lcoh_array = np.zeros(len(ratings))
                for z in np.arange(0, len(ratings)):
                    lcoh_array[z] = run_simulation(
                        electrolyzer_rating_mw=ratings[z],
                        wind_rating=wind_rating,
                        verbose=verbose,
                        show_plots=show_plots,
                        use_profast=use_profast,
                        storage_type=storage_type,
                    )
                    print(lcoh_array)
                np.savetxt(
                    output_dir
                    + f"data/lcoh_vs_rating_{storage_type}_storage_{wind_rating}MWwindplant.txt",
                    np.c_[ratings, lcoh_array],
                )

    if show_plots:
        wind_ratings = [400, 800, 1200]  # [200, 400, 600, 800]
        indexes = [(0, 0), (0, 1), (1, 0), (1, 1)]
        fig, ax = plt.subplots(2, 2, sharex=True, sharey=True, figsize=(10, 6))

        for i in np.arange(0, len(wind_ratings)):
            wind_rating = wind_ratings[i]
            data_no_storage = np.loadtxt(
                f"data/lcoh_vs_rating_none_storage_{wind_rating}MWwindplant.txt"
            )
            data_pressure_vessel = np.loadtxt(
                f"data/lcoh_vs_rating_pressure_vessel_storage_{wind_rating}MWwindplant.txt"
            )
            data_salt_cavern = np.loadtxt(
                f"data/lcoh_vs_rating_salt_cavern_storage_{wind_rating}MWwindplant.txt"
            )
            data_pipe = np.loadtxt(f"data/lcoh_vs_rating_pipe_storage_{wind_rating}MWwindplant.txt")

            ax[indexes[i]].plot(
                data_pressure_vessel[:, 0] / wind_rating,
                data_pressure_vessel[:, 1],
                label="Pressure Vessel",
            )
            ax[indexes[i]].plot(
                data_pipe[:, 0] / wind_rating, data_pipe[:, 1], label="Underground Pipe"
            )
            ax[indexes[i]].plot(
                data_salt_cavern[:, 0] / wind_rating,
                data_salt_cavern[:, 1],
                label="Salt Cavern",
            )
            ax[indexes[i]].plot(
                data_no_storage[:, 0] / wind_rating,
                data_no_storage[:, 1],
                "--k",
                label="No Storage",
            )

            ax[indexes[i]].scatter(
                data_pressure_vessel[np.argmin(data_pressure_vessel[:, 1]), 0] / wind_rating,
                np.min(data_pressure_vessel[:, 1]),
                color="k",
            )
            ax[indexes[i]].scatter(
                data_pipe[np.argmin(data_pipe[:, 1]), 0] / wind_rating,
                np.min(data_pipe[:, 1]),
                color="k",
            )
            ax[indexes[i]].scatter(
                data_salt_cavern[np.argmin(data_salt_cavern[:, 1]), 0] / wind_rating,
                np.min(data_salt_cavern[:, 1]),
                color="k",
            )
            ax[indexes[i]].scatter(
                data_no_storage[np.argmin(data_no_storage[:, 1]), 0] / wind_rating,
                np.min(data_no_storage[:, 1]),
                color="k",
                label="Optimal ratio",
            )

            ax[indexes[i]].legend(frameon=False, loc="best")

            ax[indexes[i]].set_xlim([0.2, 2.0])
            ax[indexes[i]].set_ylim([0, 25])

            ax[indexes[i]].annotate(f"{wind_rating} MW Wind Plant", (0.6, 1.0))

        ax[1, 0].set_xlabel("Electrolyzer/Wind Plant Rating Ratio")
        ax[1, 1].set_xlabel("Electrolyzer/Wind Plant Rating Ratio")
        ax[0, 0].set_ylabel("LCOH ($/kg)")
        ax[1, 0].set_ylabel("LCOH ($/kg)")

        plt.tight_layout()
        plt.savefig(output_dir + "lcoh_vs_rating_ratio.pdf", transparent=True)
        plt.show()


def run_policy_options_storage_types(
    verbose=True,
    show_plots=False,
    save_plots=False,
    use_profast=True,
    output_dir="output/",
):
    """
    Runs simulations for various storage types and policy options, calculates
    LCOH, and saves the results to a file.

    Args:
        verbose (bool, optional): If True, enables verbose output during simulations.
            Defaults to True.
        show_plots (bool, optional): If True, displays plots during simulations.
            Defaults to False.
        save_plots (bool, optional): If True, saves plots generated during simulations.
            Defaults to False.
        use_profast (bool, optional): If True, uses the PROFast tool for calculations.
            Defaults to True.
        output_dir (str, optional): Directory where the results will be saved.
            Defaults to "output/".

    Notes:
        - The function iterates over a predefined list of storage types and policy
          options to compute the LCOH for each combination.
        - Results are saved in a text file named "lcoh-with-policy.txt" in the
          specified output directory.
    """
    storage_types = ["pressure_vessel", "pipe", "salt_cavern", "none"]
    policy_options = [1, 2, 3, 4, 5, 6, 7]

    lcoh_array = np.zeros((len(storage_types), len(policy_options)))
    for i, storage_type in enumerate(storage_types):
        for j, poption in enumerate(policy_options):
            lcoh_array[i, j] = run_simulation(
                storage_type=storage_type,
                incentive_option=poption,
                verbose=verbose,
                show_plots=show_plots,
                use_profast=use_profast,
            )
        print(lcoh_array)

    savepath = Path(output_dir).resolve() / "results/"
    if not savepath.exists():
        savepath.mkdir(parents=True)
    np.savetxt(
        savepath + "lcoh-with-policy.txt",
        np.c_[np.round(lcoh_array, decimals=2)],
        header=f"rows: {''.join(storage_types)}, columns: {''.join(str(p) for p in policy_options)}",  # noqa: E501
        fmt="%.2f",
    )


def run_policy_storage_design_options(
    verbose=False,
    show_plots=False,
    save_plots=False,
    use_profast=True,
    output_dir="output/",
):
    """
    Simulates and evaluates various combinations of plant design scenarios,
    policy options, and storage types for hydrogen production.

    Args:
        verbose (bool, optional): If True, enables verbose output during the
            simulation. Defaults to False.
        show_plots (bool, optional): If True, displays plots during the
            simulation. Defaults to False.
        save_plots (bool, optional): If True, saves plots generated during
            the simulation. Defaults to False.
        use_profast (bool, optional): If True, uses the ProFAST tool for
            financial analysis. Defaults to True.
        output_dir (str, optional): Directory where output data and results
            will be saved. Defaults to "output/".

    Returns:
        None: The function saves the simulation results to CSV files in the
        specified output directory. The files include:
            - "design-storage-policy-lcoh.csv": Contains design, storage,
              policy, LCOH, LCOE, and electrolyzer capacity factor data.
            - "annual_energy_breakdown.csv": Contains annual energy
              breakdown data for each simulation scenario.
    """
    design_scenarios = [1, 2, 3, 4, 5, 6, 7]
    policy_options = [1, 2, 3, 4, 5, 6, 7]
    storage_types = ["pressure_vessel", "pipe", "salt_cavern", "none"]

    design_series = []
    policy_series = []
    storage_series = []
    lcoh_series = []
    lcoe_series = []
    electrolyzer_capacity_factor_series = []
    annual_energy_breakdown_series = {
        "design": [],
        "policy": [],
        "storage": [],
        "wind_kwh": [],
        "renewable_kwh": [],
        "grid_power_kwh": [],
        "electrolyzer_kwh": [],
        "desal_kwh": [],
        "h2_transport_compressor_power_kwh": [],
        "h2_storage_power_kwh": [],
    }

    np.zeros((len(design_scenarios), len(policy_options)))
    for design in design_scenarios:
        for policy in policy_options:
            for storage in storage_types:
                if storage != "pressure_vessel":  # and storage != "none"):
                    if design != 1 and design != 5 and design != 7:
                        print("skipping: ", design, " ", policy, " ", storage)
                        continue
                design_series.append(design)
                policy_series.append(policy)
                storage_series.append(storage)
                (
                    lcoh,
                    lcoe,
                    capex_breakdown,
                    opex_breakdown_annual,
                    pf_lcoh,
                    electrolyzer_physics_results,
                    pf_lcoe,
                    annual_energy_breakdown,
                ) = run_simulation(
                    storage_type=storage,
                    plant_design_scenario=design,
                    incentive_option=policy,
                    verbose=verbose,
                    show_plots=show_plots,
                    use_profast=use_profast,
                    output_level=3,
                )
                lcoh_series.append(lcoh)
                lcoe_series.append(lcoe)
                electrolyzer_capacity_factor_series.append(
                    electrolyzer_physics_results["H2_Results"]["Life: Capacity Factor"]
                )

                annual_energy_breakdown_series["design"].append(design)
                annual_energy_breakdown_series["policy"].append(policy)
                annual_energy_breakdown_series["storage"].append(storage)
                for key in annual_energy_breakdown.keys():
                    annual_energy_breakdown_series[key].append(annual_energy_breakdown[key])

    savepath = Path(output_dir).resolve() / "data/"
    if not savepath.exists():
        savepath.mkdir(parents=True)
    df = pd.DataFrame.from_dict(
        {
            "Design": design_series,
            "Storage": storage_series,
            "Policy": policy_series,
            "LCOH [$/kg]": lcoh_series,
            "LCOE [$/kWh]": lcoe_series,
            "Electrolyzer capacity factor": electrolyzer_capacity_factor_series,
        }
    )
    df.to_csv(savepath + "design-storage-policy-lcoh.csv")

    df_energy = pd.DataFrame.from_dict(annual_energy_breakdown_series)
    df_energy.to_csv(savepath + "annual_energy_breakdown.csv")


def run_design_options(
    verbose=False,
    show_plots=False,
    save_plots=False,
    incentive_option=1,
    output_dir="output/",
):
    """
    Runs simulations for multiple plant design scenarios and aggregates results.

    This function iterates through a range of plant design scenarios, runs simulations
    for each design, and collects key performance metrics. The results
    are then saved as CSV files in the specified output directory.

    Args:
        verbose (bool, optional): If True, enables verbose logging during simulations.
            Defaults to False.
        show_plots (bool, optional): If True, displays plots during simulations.
            Defaults to False.
        save_plots (bool, optional): If True, saves plots generated during simulations.
            Defaults to False.
        incentive_option (int, optional): Specifies the incentive option to use in the
            simulation. Defaults to 1.
        output_dir (str, optional): Directory where the output CSV files will be saved.
            Defaults to "output/".

    Outputs:
        Three CSV files are saved in the `output_dir/combined_results/` directory:
        - `metrics.csv`: Contains aggregated metrics such as LCOH and LCOE for each design.
        - `capex.csv`: Contains CAPEX breakdown for each design.
        - `opex.csv`: Contains OPEX breakdown for each design.
    """
    design_options = range(1, 8)  # 8
    scenario_lcoh = []
    scenario_lcoe = []
    scenario_capex_breakdown = []
    scenario_opex_breakdown_annual = []
    scenario_pf = []
    scenario_electrolyzer_physics = []

    for design in design_options:
        (
            lcoh,
            lcoe,
            capex_breakdown,
            opex_breakdown_annual,
            pf,
            electrolyzer_physics_results,
        ) = run_simulation(
            verbose=verbose,
            show_plots=show_plots,
            use_profast=True,
            incentive_option=incentive_option,
            plant_design_scenario=design,
            output_level=2,
        )
        scenario_lcoh.append(lcoh)
        scenario_lcoe.append(lcoe)
        scenario_capex_breakdown.append(capex_breakdown)
        scenario_opex_breakdown_annual.append(opex_breakdown_annual)
        scenario_pf.append(pf)
        scenario_electrolyzer_physics.append(electrolyzer_physics_results)
    df_aggregate = pd.DataFrame.from_dict(
        {
            "Design": [int(x) for x in design_options],
            "LCOH [$/kg]": scenario_lcoh,
            "LCOE [$/kWh]": scenario_lcoe,
        }
    )
    df_capex = pd.DataFrame(scenario_capex_breakdown)
    df_opex = pd.DataFrame(scenario_opex_breakdown_annual)

    df_capex.insert(0, "Design", design_options)
    df_opex.insert(0, "Design", design_options)

    # df_aggregate = df_aggregate.transpose()
    df_capex = df_capex.transpose()
    df_opex = df_opex.transpose()

    results_path = Path(output_dir).resolve() / "combined_results/"
    if not results_path.exists():
        results_path.mkdir(parents=True)
    df_aggregate.to_csv(results_path + "metrics.csv")
    df_capex.to_csv(results_path + "capex.csv")
    df_opex.to_csv(results_path + "opex.csv")


def run_storage_options(output_dir="output/"):
    """
    Runs simulations for various hydrogen storage options and saves the results to a CSV file.

    Args:
        output_dir (str): Directory where the output CSV file will be saved. Defaults to "output/".
    Notes:
        - The storage types evaluated are "pressure_vessel", "pipe", "salt_cavern", and "none".
        - The results include LCOE, LCOH, LCOH with grid connection, and LCOH for
            grid-only scenarios.
        - The output CSV file is saved in a subdirectory named "data/" within the specified
            output directory.
    """
    storage_types = ["pressure_vessel", "pipe", "salt_cavern", "none"]
    lcoe_list = []
    lcoh_list = []
    lcoh_with_grid_list = []
    lcoh_grid_only_list = []
    for storage_type in storage_types:
        lcoe, lcoh, _ = run_simulation(
            verbose=False,
            show_plots=False,
            save_plots=False,
            use_profast=True,
            incentive_option=1,
            plant_design_scenario=1,
            storage_type=storage_type,
            output_level=4,
            grid_connection=False,
            output_dir=output_dir,
        )
        lcoe_list.append(lcoe)
        lcoh_list.append(lcoh)

        # with grid
        _, lcoh_with_grid, lcoh_grid_only = run_simulation(
            verbose=False,
            show_plots=False,
            save_plots=False,
            use_profast=True,
            incentive_option=1,
            plant_design_scenario=1,
            storage_type=storage_type,
            output_level=4,
            grid_connection=True,
            output_dir=output_dir,
        )
        lcoh_with_grid_list.append(lcoh_with_grid)
        lcoh_grid_only_list.append(lcoh_grid_only)

    data_dict = {
        "Storage Type": storage_types,
        "LCOE [$/MW]": np.asarray(lcoe_list) * 1e3,
        "LCOH [$/kg]": lcoh_list,
        "LCOH with Grid [$/kg]": lcoh_with_grid_list,
        "LCOH Grid Only [$/kg]": lcoh_grid_only_list,
    }
    df = pd.DataFrame.from_dict(data_dict)

    savepath = Path(output_dir).resolve() / "data/"
    if not savepath.exists():
        savepath.mkdir(parents=True)
    df.to_csv(savepath + "storage-types-and-matrics.csv")
