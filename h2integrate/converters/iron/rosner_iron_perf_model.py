import numpy as np
import pandas as pd
import openmdao.api as om
from attrs import field, define
from openmdao.utils import units

from h2integrate import ROOT_DIR
from h2integrate.core.utilities import BaseConfig, merge_shared_inputs


@define
class NaturalGasIronReductionPerformanceConfig(BaseConfig):
    """Configuration class for NaturalGasIronReductionPlantPerformanceComponent.

    Attributes:
        pig_iron_production_rate_tonnes_per_hr (float): capacity of the iron processing plant
            in units of metric tonnes of pig iron produced per hour.
        water_density (float): water density in kg/m3 to use to calculate water volume
            from mass. Defaults to 1000.0
    """

    pig_iron_production_rate_tonnes_per_hr: float = field()
    water_density: float = field(default=1000)  # kg/m3


class NaturalGasIronReductionPlantPerformanceComponent(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        self.config = NaturalGasIronReductionPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=True,
        )

        self.add_input(
            "system_capacity",
            val=self.config.pig_iron_production_rate_tonnes_per_hr,
            units="t/h",
            desc="Rated pig iron production capacity",
        )

        feedstocks_to_units = {
            "natural_gas": "MMBtu",
            "water": "galUS",  # "galUS/h"
            "iron_ore": "t/h",
            "electricity": "kW",
            "reformer_catalyst": "(m**3)",  # "(m**3)/h"
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
            self.add_output(
                f"{feedstock}_consumed",
                val=0.0,
                shape=n_timesteps,
                units=feedstock_units,
                desc=f"{feedstock} consumed for iron reduction",
            )

        # Default the pig iron demand input as the rated capacity
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

        coeff_fpath = ROOT_DIR / "converters" / "iron" / "rosner" / "perf_coeffs.csv"
        # rosner dri performance model
        coeff_df = pd.read_csv(coeff_fpath, index_col=0)
        self.coeff_df = self.format_coeff_df(coeff_df)
        self.feedstock_to_units = feedstocks_to_units

    def format_coeff_df(self, coeff_df):
        """Update the coefficient dataframe such that feedstock values are converted to units of
        feedstock unit / unit pig iron, e.g., 'galUS/t'. Also convert values to standard units
        and that units are compatible with OpenMDAO Units. Filter the dataframe to include
        only the data necessary for Natural Gas reduction.

        Args:
            coeff_df (pd.DataFrame): performance coefficient dataframe.

        Returns:
            pd.DataFrame: filtered performance coefficient dataframe
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
        steel_plant_capacity = coeff_df[coeff_df["Name"] == "Steel Production"]["Value"].values[0]
        iron_plant_capacity = coeff_df[coeff_df["Name"] == "Pig Iron Production"]["Value"].values[0]

        # capacity units units are mtpy
        steel_to_iron_ratio = steel_plant_capacity / iron_plant_capacity  # both in metric tons/year
        unit_rename_mapper = {"mtpy": "t/yr", "%": "unitless"}

        # efficiency units are %
        # feedstock units are mt ore/mt steel, m3 catalyst/mt steel, GJ-LHV NG/mt steel,
        # mt H2O/mt steel, kW/mtpy steel

        # convert units to standardized units
        old_units = list(set(coeff_df["Unit"].to_list()))
        for ii, old_unit in enumerate(old_units):
            if old_unit in unit_rename_mapper:
                continue
            if "steel" in old_unit:
                feedstock_unit, capacity_unit = old_unit.split("/")
                capacity_unit = capacity_unit.replace("steel", "").strip()
                feedstock_unit = feedstock_unit.strip()

                i_update = coeff_df[coeff_df["Unit"] == old_unit].index

                # convert from feedstock per unit steel to feedstock per unit pig iron
                coeff_df.loc[i_update]["Value"] = (
                    coeff_df.loc[i_update]["Value"] * steel_to_iron_ratio
                )

                # update the "Type" to specify that units were changed to be per unit pig iron
                coeff_df.loc[i_update]["Type"] = f"{coeff_df.loc[i_update]['Type'].values[0]}/iron"

                is_capacity_type = all(
                    k == "capacity" for k in coeff_df.loc[i_update]["Type"].to_list()
                )
                if capacity_unit == "mtpy" and not is_capacity_type:
                    # some feedstocks had misleading units,
                    # where 'kW/ mtpy steel' is actually 'kW/mt steel'
                    # NOTE: perhaps these ones need to be modified with the steel efficiency?
                    capacity_unit = "mt"

                old_unit = f"{feedstock_unit}/{capacity_unit}"

            if "H2O" in old_unit:
                # convert metric tonnes to kg (value*1e3)
                # convert mass to volume in cubic meters (value*1e3)/density
                # then convert cubic meters to liters 1e3*(value*1e3)/density
                water_volume_m3 = coeff_df.loc[i_update]["Value"] * 1e3 / self.config.water_density
                water_volume_L = units.convert_units(water_volume_m3.values, "m**3", "L")
                coeff_df.loc[i_update]["Value"] = water_volume_L
                old_unit = f"L/{capacity_unit}"

            old_unit = old_unit.replace("-LHV NG", "").replace("%", "percent")
            old_unit = (
                old_unit.replace("m3 catalyst", "(m**3)")
                .replace("MWh", "(MW*h)")
                .replace(" ore", "")
            )
            old_unit = (
                old_unit.replace("mtpy", "(t/yr)").replace("mt", "t").replace("kW/", "(kW*h)/")
            )
            # NOTE: how would 'kW / mtpy steel' be different than 'kW / mt steel'
            # replace % with "unitless"
            unit_rename_mapper.update({old_units[ii]: old_unit})
        coeff_df["Unit"] = coeff_df["Unit"].replace(to_replace=unit_rename_mapper)

        convert_units_dict = {
            "GJ/t": "MMBtu/t",
            "L/t": "galUS/t",
            "(MW*h)/t": "(kW*h)/t",
            "percent": "unitless",
        }
        # convert units to standard units and OpenMDAO compatible units
        for i in coeff_df.index.to_list():
            if coeff_df.loc[i, "Unit"] in convert_units_dict:
                current_units = coeff_df.loc[i, "Unit"]
                desired_units = convert_units_dict[current_units]
                coeff_df.loc[i, "Value"] = units.convert_units(
                    coeff_df.loc[i, "Value"], current_units, desired_units
                )
                coeff_df.loc[i, "Unit"] = desired_units
                # NOTE: not sure if percent is actually being converted to unitless
                # but not big deal since percent is not used in feedstocks
        return coeff_df

    def compute(self, inputs, outputs):
        # get the feedstocks from
        feedstocks = self.coeff_df[self.coeff_df["Type"] == "feed"].copy()

        # get the feedstock usage rates in units/t pig iron
        feedstocks_usage_rates = {
            "natural_gas": feedstocks[feedstocks["Unit"] == "MMBtu/t"]["Value"].sum(),
            "water": feedstocks[feedstocks["Unit"] == "galUS/t"]["Value"].sum(),
            "iron_ore": feedstocks[feedstocks["Name"] == "Iron Ore"]["Value"].sum(),
            "electricity": feedstocks[feedstocks["Unit"] == "(kW*h)/t"]["Value"].sum(),
            "reformer_catalyst": feedstocks[feedstocks["Name"] == "Reformer Catalyst"][
                "Value"
            ].sum(),
        }

        # pig iron demand, saturated at maximum rated system capacity
        pig_iron_demand = np.where(
            inputs["pig_iron_demand"] > inputs["system_capacity"],
            inputs["system_capacity"],
            inputs["pig_iron_demand"],
        )

        # initialize an array of how much pig iron could be produced
        # from the available feedstocks and the demand
        pig_iron_from_feedstocks = np.zeros(
            (len(feedstocks_usage_rates) + 1, len(inputs["pig_iron_demand"]))
        )
        # first entry is the pig iron demand
        pig_iron_from_feedstocks[0] = pig_iron_demand
        ii = 1
        for feedstock_type, consumption_rate in feedstocks_usage_rates.items():
            # calculate max inputs/outputs based on rated capacity
            max_feedstock_consumption = inputs["system_capacity"] * consumption_rate
            # available feedstocks, saturated at maximum system feedstock consumption
            feedstock_available = np.where(
                inputs[f"{feedstock_type}_in"] > max_feedstock_consumption,
                max_feedstock_consumption,
                inputs[f"{feedstock_type}_in"],
            )
            # how much output can be produced from each of the feedstocks
            pig_iron_from_feedstocks[ii] = feedstock_available / consumption_rate
            ii += 1

        # output is minimum between available feedstocks and output demand
        pig_iron_production = np.minimum.reduce(pig_iron_from_feedstocks)
        outputs["pig_iron_out"] = pig_iron_production

        # feedstock consumption based on actual pig iron produced
        for feedstock_type, consumption_rate in feedstocks_usage_rates.items():
            outputs[f"{feedstock_type}_consumed"] = pig_iron_production * consumption_rate


if __name__ == "__main__":
    prob = om.Problem()

    plant_config = {"plant": {"simulation": {"n_timesteps": 8760}}}
    iron_dri_config_rosner_ng = {
        "pig_iron_production_rate_tonnes_per_hr": 1418095 / 8760,
    }
    iron_dri_perf = NaturalGasIronReductionPlantPerformanceComponent(
        plant_config=plant_config,
        tech_config={"model_inputs": {"performance_parameters": iron_dri_config_rosner_ng}},
        driver_config={},
    )
    prob.model.add_subsystem("dri", iron_dri_perf, promotes=["*"])
    prob.setup()
    prob.run_model()
