import pandas as pd
import openmdao.api as om
from attrs import field, define
from openmdao.utils import units

from h2integrate import ROOT_DIR
from h2integrate.core.utilities import CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.validators import gte_zero
from h2integrate.core.model_baseclasses import CostModelBaseClass
from h2integrate.tools.inflation.inflate import inflate_cpi, inflate_cepci


@define
class NaturalGasIronReductionCostConfig(CostModelBaseConfig):
    """Configuration class for NaturalGasIronReductionPlantCostComponent.

    Attributes:
        pig_iron_production_rate_tonnes_per_hr (float): capacity of the iron processing plant
            in units of metric tonnes of pig iron produced per hour.
        cost_year (int): This model uses 2022 as the base year for the cost model.
            The cost year is updated based on `target_dollar_year` in the plant
            config to adjust costs based on CPI/CEPCI within this model. This value
            cannot be user added under `cost_parameters`.
        skilled_labor_cost (float): Skilled labor cost in 2022 USD/hr
        unskilled_labor_cost (float): Unskilled labor cost in 2022 USD/hr
    """

    pig_iron_production_rate_tonnes_per_hr: float = field()
    cost_year: int = field(converter=int)
    skilled_labor_cost: float = field(validator=gte_zero)
    unskilled_labor_cost: float = field(validator=gte_zero)


class NaturalGasIronReductionPlantCostComponent(CostModelBaseClass):
    """Calculates the capital and operating costs for a natural gas-based direct
    iron reduction plant using the Rosner cost model.

    Attributes:
        config (NaturalGasIronReductionCostConfig): configuration class
        coeff_df (pd.DataFrame): cost coefficient dataframe
        steel_to_iron_ratio (float): steel/pig iron ratio
    """

    def setup(self):
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        config_dict = merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")

        if "cost_year" in config_dict:
            msg = (
                "This cost model is based on 2022 costs and adjusts costs using CPI and CEPCI. "
                "The cost year cannot be modified for this cost model. "
            )
            raise ValueError(msg)

        target_dollar_year = self.options["plant_config"]["finance_parameters"][
            "cost_adjustment_parameters"
        ]["target_dollar_year"]

        if target_dollar_year <= 2024 and target_dollar_year >= 2010:
            # adjust costs from 2022 to target dollar year using CPI/CEPCI adjustment
            target_dollar_year = target_dollar_year

        elif target_dollar_year < 2010:
            # adjust costs from 2022 to 2010 using CP/CEPCI adjustment
            target_dollar_year = 2010

        elif target_dollar_year > 2024:
            # adjust costs from 2022 to 2024 using CPI/CEPCI adjustment
            target_dollar_year = 2024

        config_dict.update({"cost_year": target_dollar_year})

        self.config = NaturalGasIronReductionCostConfig.from_dict(config_dict, strict=False)

        super().setup()

        self.add_input(
            "system_capacity",
            val=self.config.pig_iron_production_rate_tonnes_per_hr,
            units="t/h",
            desc="Pig ore production capacity",
        )
        self.add_input(
            "pig_iron_out",
            val=0.0,
            shape=n_timesteps,
            units="t/h",
            desc="Pig iron produced",
        )

        coeff_fpath = ROOT_DIR / "converters" / "iron" / "rosner" / "cost_coeffs.csv"
        # rosner cost model
        coeff_df = pd.read_csv(coeff_fpath, index_col=0)
        self.coeff_df = self.format_coeff_df(coeff_df)

    def format_coeff_df(self, coeff_df):
        """Update the coefficient dataframe such that values are adjusted to standard units
            and units are compatible with OpenMDAO units. Also filter the dataframe to include
            only the data necessary for natural gas DRI type.

        Args:
            coeff_df (pd.DataFrame): cost coefficient dataframe.

        Returns:
            pd.DataFrame: cost coefficient dataframe
        """
        product = "ng_dri"  # h2_dri

        perf_coeff_fpath = ROOT_DIR / "converters" / "iron" / "rosner" / "perf_coeffs.csv"

        perf_df = pd.read_csv(perf_coeff_fpath, index_col=0)
        perf_df = perf_df[perf_df["Product"] == product]
        steel_plant_capacity = perf_df[perf_df["Name"] == "Steel Production"]["Model"].values[0]
        iron_plant_capacity = perf_df[perf_df["Name"] == "Pig Iron Production"]["Model"].values[0]
        steel_to_iron_ratio = steel_plant_capacity / iron_plant_capacity  # both in metric tons/year
        self.steel_to_iron_ratio = steel_to_iron_ratio

        # only include data for the given product

        data_cols = ["Type", "Coeff", "Unit", product]
        coeff_df = coeff_df[data_cols]

        coeff_df = coeff_df.rename(columns={product: "Value"})

        return coeff_df

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # Calculate the capital cost for the item
        dollar_year = self.coeff_df.loc["Dollar Year", "Value"].astype(int)

        # Calculate
        capital_items = list(set(self.coeff_df[self.coeff_df["Type"] == "capital"].index.to_list()))
        capital_items_df = self.coeff_df.loc[capital_items].copy()
        capital_items_df = capital_items_df.reset_index(drop=False)
        capital_items_df = capital_items_df.set_index(
            keys=["Name", "Coeff"]
        )  # costs are in USD/steel plant capacity
        capital_items_df = capital_items_df.drop(columns=["Unit", "Type"])

        ref_steel_plant_capacity_tpy = units.convert_units(
            inputs["system_capacity"] * self.steel_to_iron_ratio, "t/h", "t/yr"
        )

        total_capex_usd = 0.0
        for item in capital_items:
            if (
                capital_items_df.loc[item, "exp"]["Value"] > 0
                and capital_items_df.loc[item, "lin"]["Value"] > 0
            ):
                capex = capital_items_df.loc[item, "lin"]["Value"] * (
                    (ref_steel_plant_capacity_tpy) ** capital_items_df.loc[item, "exp"]["Value"]
                )
                total_capex_usd += inflate_cepci(capex, dollar_year, self.config.cost_year)

        # Calculate Owners Costs
        # owner_costs_frac_tpc = self.coeff_df[self.coeff_df["Type"]=="owner"]["Value"].sum()

        # Calculate Fixed OpEx, includes:
        fixed_items = list(
            set(self.coeff_df[self.coeff_df["Type"] == "fixed opex"].index.to_list())
        )
        fixed_items_df = self.coeff_df.loc[fixed_items].copy()
        fixed_items_df = fixed_items_df.reset_index(drop=False)
        fixed_items_df = fixed_items_df.set_index(keys=["Name", "Coeff"])
        fixed_items_df = fixed_items_df.drop(columns=["Type"])

        property_om = (
            total_capex_usd * fixed_items_df.loc["Property Tax & Insurance"]["Value"].sum()
        )

        # Calculate labor costs
        skilled_labor_cost = self.config.skilled_labor_cost * (
            fixed_items_df.loc["% Skilled Labor"]["Value"].values / 100
        )
        unskilled_labor_cost = self.config.unskilled_labor_cost * (
            fixed_items_df.loc["% Unskilled Labor"]["Value"].values / 100
        )
        labor_cost_per_hr = skilled_labor_cost + unskilled_labor_cost  # USD/hr

        ref_steel_plant_capacity_kgpd = units.convert_units(
            inputs["system_capacity"] * self.steel_to_iron_ratio, "t/h", "kg/d"
        )
        scaled_steel_plant_capacity_kgpd = (
            ref_steel_plant_capacity_kgpd
            ** fixed_items_df.loc["Annual Operating Labor Cost", "exp"]["Value"]
        )

        # employee-hours/day/process step = ((employee-hours/day/process step)/(kg/day))*(kg/day)
        work_hrs_per_day_per_step = (
            scaled_steel_plant_capacity_kgpd
            * fixed_items_df.loc["Annual Operating Labor Cost", "lin"]["Value"]
        )

        # employee-hours/day = employee-hours/day/process step * # of process steps
        work_hrs_per_day = (
            work_hrs_per_day_per_step * fixed_items_df.loc["Processing Steps"]["Value"].values
        )
        labor_cost_per_day = labor_cost_per_hr * work_hrs_per_day
        annual_labor_cost = labor_cost_per_day * units.convert_units(1, "yr", "d")
        maintenance_labor_cost = (
            total_capex_usd * fixed_items_df.loc["Maintenance Labor Cost"]["Value"].values
        )
        admin_labor_cost = fixed_items_df.loc["Administrative & Support Labor Cost"][
            "Value"
        ].values * (annual_labor_cost + maintenance_labor_cost)

        total_labor_related_cost = admin_labor_cost + maintenance_labor_cost + annual_labor_cost
        tot_fixed_om = total_labor_related_cost + property_om

        # Calculate Variable O&M
        varom = self.coeff_df[self.coeff_df["Type"] == "variable opex"][
            "Value"
        ].sum()  # units are USD/mtpy steel
        tot_varopex = varom * self.steel_to_iron_ratio * inputs["pig_iron_out"].sum()

        # Adjust costs to target dollar year
        tot_capex_adjusted = inflate_cepci(total_capex_usd, dollar_year, self.config.cost_year)
        tot_fixed_om_adjusted = inflate_cpi(tot_fixed_om, dollar_year, self.config.cost_year)
        tot_varopex_adjusted = inflate_cpi(tot_varopex, dollar_year, self.config.cost_year)

        outputs["CapEx"] = tot_capex_adjusted
        outputs["VarOpEx"] = tot_varopex_adjusted
        outputs["OpEx"] = tot_fixed_om_adjusted


if __name__ == "__main__":
    prob = om.Problem()

    plant_config = {
        "plant": {"plant_life": 30, "simulation": {"n_timesteps": 8760}},
        "finance_parameters": {"cost_adjustment_parameters": {"target_dollar_year": 2022}},
    }
    iron_dri_config_rosner_ng = {
        "pig_iron_production_rate_tonnes_per_hr": 1418095 / 8760,
        "skilled_labor_cost": 1.0,
        "unskilled_labor_cost": 1.0,
    }
    iron_dri_perf = NaturalGasIronReductionPlantCostComponent(
        plant_config=plant_config,
        tech_config={"model_inputs": {"shared_parameters": iron_dri_config_rosner_ng}},
        driver_config={},
    )
    prob.model.add_subsystem("dri", iron_dri_perf, promotes=["*"])
    prob.setup()
    prob.run_model()
