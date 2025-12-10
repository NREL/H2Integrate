import numpy as np
import pandas as pd
import openmdao.api as om
from attrs import field, define
from openmdao.utils import units

from h2integrate import ROOT_DIR
from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains


@define
class RosnerIronPlantPerformanceConfig(BaseConfig):
    """Configuration class for MartinIronMinePerformanceComponent.

    Attributes:
        taconite_pellet_type (str): type of taconite pellets, options are "std" or "drg".
        mine (str): name of ore mine. Must be "Hibbing", "Northshore", "United",
            "Minorca" or "Tilden"
        pig_iron_production_rate_tonnes_per_hr (float): capacity of the iron processing plant
            in units of metric tonnes of pig iron produced per hour.
    """

    pig_iron_production_rate_tonnes_per_hr: float = field()

    reduction_chemical: str = field(
        converter=(str.lower, str.strip), validator=contains(["ng", "h2"])
    )

    mine: str = field(validator=contains(["Hibbing", "Northshore", "United", "Minorca", "Tilden"]))


class NaturalGasIronReudctionPlantPerformanceComponent(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        self.config = RosnerIronPlantPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=True,
        )

        self.add_input(
            "system_capacity",
            val=self.config.pig_iron_production_rate_tonnes_per_hr,
            units="t/h",
            desc="Annual pig iron production capacity",
        )

        feedstocks_to_units = {
            "natural_gas": "MMBtu",
            "water": "gal/h",
            "iron_ore": "t/h",
            "electricity": "kW",
            "reformer_catalyst": "(m**3)/h",
        }
        # Add feedstock inputs and outputs, default to 0 --> set using feedstock component
        for feedstock, feedstock_units in feedstocks_to_units.items():
            self.add_input(
                f"{feedstock}_in",
                val=0.0,
                shape=n_timesteps,
                units=feedstock_units,
                desc=f"{feedstock} available for iron reduction",
            )
            self.add_input(
                f"{feedstock}_in",
                val=0.0,
                shape=n_timesteps,
                units=feedstock_units,
                desc=f"{feedstock} consumed for iron reduction",
            )

        # Add iron ore input, default to 0 --> set using feedstock component

        # Default the reduced iron demand input as the rated capacity
        self.add_input(
            "system_capacity",
            val=self.config.pig_iron_production_rate_tonnes_per_hr,
            # shape=n_timesteps,
            units="t/h",
            desc="Annual ore production capacity",
        )

        self.add_input(
            "pig_iron_demand",
            val=self.config.pig_iron_production_rate_tonnes_per_hr,
            shape=n_timesteps,
            units="t/h",
            desc="Pig iron demand for iron plant",
        )

        self.add_output(
            "pig_iron_out",
            val=0.0,
            shape=n_timesteps,
            units="t/h",
            desc="Pig iron produced",
        )

        coeff_fpath = (
            ROOT_DIR / "simulation" / "technologies" / "iron" / "rosner" / "perf_coeffs.csv"
        )
        # martin ore performance model
        coeff_df = pd.read_csv(coeff_fpath, index_col=0)
        self.coeff_df = self.format_coeff_df(coeff_df, self.config.mine)

    def format_coeff_df(self, coeff_df):
        """Update the coefficient dataframe such that values are adjusted to standard units
            and units are compatible with OpenMDAO units. Also filter the dataframe to include
            only the data necessary for a given mine and pellet type.

        Args:
            coeff_df (pd.DataFrame): cost coefficient dataframe.
            mine (str): name of mine that ore is extracted from.

        Returns:
            pd.DataFrame: cost coefficient dataframe
        """
        # only include data for the given product
        coeff_df = coeff_df[coeff_df["Product"] == "ng_dri"]
        data_cols = ["Name", "Type", "Coeff", "Unit", "Model"]
        coeff_df = coeff_df[data_cols]
        coeff_df = coeff_df.rename(columns={"Model": "Value"})
        coeff_df = coeff_df[coeff_df["Value"] > 0]
        coeff_df = coeff_df[coeff_df["Type"] != "emission"]  # dont include emission data

        # ng DRI needs natural gas, water, electricity, iron ore and reformer catalyst
        # h2_dri needs natural gas, water, hydrogen, iron ore.
        # hm.loc["ng_dri","feed"][hm.loc["ng_dri","feed"]["Model"]>0]
        steel_plant_capacity = coeff_df[coeff_df["Name"] == "Steel Production"]
        iron_plant_capacity = coeff_df[coeff_df["Name"] == "Pig Iron Production"]

        steel_to_iron_ratio = steel_plant_capacity / iron_plant_capacity  # both in metric tons/year
        unit_rename_mapper = {"mtpy": "t/yr", "%": "unitless"}

        # units are mtpy, %, mt ore/mt steel, m3 catalyst/mt steel, GJ-LHV NG/mt steel,
        # mt H2O/mt steel, mt CO2/mt steel, mt H20 discharged/mt H2O withdrawn, kW/mtpy steel
        # convert wet long tons per year to dry long tons per year

        # convert units to standardized units
        old_units = list(set(coeff_df["Unit"].to_list()))
        for ii, old_unit in enumerate(old_units):
            if old_unit in unit_rename_mapper:
                continue
            if "steel" in old_unit:
                feedstock_unit, capacity_unit = old_unit.split("/")

                i_update = coeff_df[coeff_df["Unit"] == old_unit].index
                # convert from feedstock per unit steel to feedstock per unit pig iron
                coeff_df.loc[i_update]["Model"] = (
                    coeff_df.loc[i_update]["Model"] * steel_to_iron_ratio
                )
                # TODO: update name

                # if 'mtpy' in capacity_unit:
                #     # convert from amount/annual steel to amount/unit pig iron
                #     total_feedstock_usage = coeff_df.loc[i_update]["Model"]*steel_plant_capacity
                #     feedstock_usage_ratio = total_feedstock_usage/iron_plant_capacity
                # if 'mt ' in capacity_unit:

            if "MWh" in old_unit:
                old_unit = old_unit.replace("MWh", "(MW*h)")
            if "mlt" in old_unit:  # millon long tons
                old_unit = old_unit.replace("mlt", "(2240*Mlb)")
            if "lt" in old_unit:  # dry long tons
                old_unit = old_unit.replace("lt", "(2240*lb)")
            if "mt" in old_unit:  # metric tonne
                old_unit = old_unit.replace("mt", "t")
            if "wt %" in old_unit:
                old_unit = old_unit.replace("wt %", "unitless")
            if "deg N" in old_unit or "deg E" in old_unit:
                old_unit = "deg"
            unit_rename_mapper.update({old_units[ii]: old_unit})
        coeff_df["Unit"] = coeff_df["Unit"].replace(to_replace=unit_rename_mapper)

        convert_units_dict = {
            "(kW*h)/(2240*lb)": "(kW*h)/t",
            "(2240*Mlb)": "t",
            "(2240*lb)/yr": "t/yr",
        }
        for i in coeff_df.index.to_list():
            if coeff_df.loc[i, "Unit"] in convert_units_dict:
                current_units = coeff_df.loc[i, "Unit"]
                desired_units = convert_units_dict[current_units]
                coeff_df.loc[i, "Value"] = units.convert_units(
                    coeff_df.loc[i, "Value"], current_units, desired_units
                )
                coeff_df.loc[i, "Unit"] = desired_units

        return coeff_df

    def compute(self, inputs, outputs):
        # calculate crude ore required per amount of ore processed
        ref_Orefeedstock = self.coeff_df[self.coeff_df["Name"] == "Crude ore processed"][
            "Value"
        ].values
        ref_Oreproduced = self.coeff_df[self.coeff_df["Name"] == "Ore pellets produced"][
            "Value"
        ].values
        crude_ore_usage_per_processed_ore = ref_Orefeedstock / ref_Oreproduced

        # energy consumption based on ore production
        energy_usage_per_processed_ore = self.coeff_df[
            self.coeff_df["Type"] == "energy use/pellet"
        ]["Value"].sum()
        # check that units work out
        energy_usage_unit = self.coeff_df[self.coeff_df["Type"] == "energy use/pellet"][
            "Unit"
        ].values[0]
        energy_usage_per_processed_ore = units.convert_units(
            energy_usage_per_processed_ore, f"(t/h)*({energy_usage_unit})", "(kW*h)/h"
        )

        # calculate max inputs/outputs based on rated capacity
        max_crude_ore_consumption = inputs["system_capacity"] * crude_ore_usage_per_processed_ore
        max_energy_consumption = inputs["system_capacity"] * energy_usage_per_processed_ore

        # iron ore demand, saturated at maximum rated system capacity
        processed_ore_demand = np.where(
            inputs["iron_ore_demand"] > inputs["system_capacity"],
            inputs["system_capacity"],
            inputs["iron_ore_demand"],
        )

        # available feedstocks, saturated at maximum system feedstock consumption
        crude_ore_available = np.where(
            inputs["crude_ore_in"] > max_crude_ore_consumption,
            max_crude_ore_consumption,
            inputs["crude_ore_in"],
        )

        energy_available = np.where(
            inputs["electricity_in"] > max_energy_consumption,
            max_energy_consumption,
            inputs["electricity_in"],
        )

        # how much output can be produced from each of the feedstocks
        processed_ore_from_electricity = energy_available / energy_usage_per_processed_ore
        processed_ore_from_crude_ore = crude_ore_available / crude_ore_usage_per_processed_ore

        # output is minimum between available feedstocks and output demand
        processed_ore_production = np.minimum.reduce(
            [processed_ore_from_crude_ore, processed_ore_from_electricity, processed_ore_demand]
        )

        # energy consumption
        energy_consumed = processed_ore_production * energy_usage_per_processed_ore

        # crude ore consumption
        crude_ore_consumption = processed_ore_production * crude_ore_usage_per_processed_ore

        outputs["iron_ore_out"] = processed_ore_production
        outputs["electricity_consumed"] = energy_consumed
        outputs["crude_ore_consumed"] = crude_ore_consumption
