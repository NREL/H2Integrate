import numpy as np
from attrs import field, define
from openmdao.utils.units import convert_units

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.converters.methanol.methanol_baseclass import (
    MethanolCostConfig,
    MethanolCostBaseClass,
    MethanolFinanceConfig,
    MethanolFinanceBaseClass,
    MethanolPerformanceConfig,
    MethanolPerformanceBaseClass,
)


@define
class CO2HPerformanceConfig(MethanolPerformanceConfig):
    meoh_syn_cat_consume_ratio: float = field()
    ng_consume_ratio: float = field()
    co2_consume_ratio: float = field()
    h2_consume_ratio: float = field()
    elec_consume_ratio: float = field()


class CO2HMethanolPlantPerformanceModel(MethanolPerformanceBaseClass):
    """
    An OpenMDAO component for modeling the performance of a CO2 Hydrogenation (CO2H) methanol
    plant. Computes annual methanol and co-product production, feedstock consumption, and emissions
    based on plant capacity and capacity factor.

    Inputs:
        - meoh_syn_cat_consume_ratio: ratio of ft^3 methanol synthesis catalyst consumed to
            kg methanol produced
        - meoh_atr_cat_consume_ratio: ratio of ft^3 methanol autothermal reforming (ATR) catalyst
            consumed to kg methanol produced
        - ng_consume_ratio: ratio of kg natural gas (NG) consumed to kg methanol produced
        - co2_consume_ratio: ratio of kg co2 consumed to kg methanol produced
        - elec_consume_ratio: ratio of kWh electricity consumed to kg methanol produced
    Outputs:
        - meoh_syn_cat_required: annual consumption of methanol synthesis catalyst (ft**3/yr)
        - ng_required: hourly consumption of NG (kg/h)
        - carbon dioxide_required: co2 consumption in kg/h
        - hydrogen_required: h2 consumption in kg/h
        - electricity_required: electricity consumption in kWh/h
    """

    def setup(self):
        self.config = CO2HPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        super().setup()

        # Add in tech-specific variables and values
        self.add_input(
            "meoh_syn_cat_consume_ratio",
            units="ft**3/kg",
            val=self.config.meoh_syn_cat_consume_ratio,
        )
        self.add_input("ng_consume_ratio", units="kg/kg", val=self.config.ng_consume_ratio)
        self.add_input("co2_consume_ratio", units="kg/kg", val=self.config.co2_consume_ratio)
        self.add_input("h2_consume_ratio", units="kg/kg", val=self.config.h2_consume_ratio)
        self.add_input("elec_consume_ratio", units="kg/kW/h", val=self.config.elec_consume_ratio)

        # Hydrogen input comes from another converter, and is in kg/s
        self.add_input("hydrogen_in", shape=8760, units="kg/s")
        self.add_output("hydrogen_required", units="kg/yr")
        self.add_output("hydrogen_capacity", units="kg/yr")
        self.add_output("methanol_capacity", units="kg/yr")

        self.add_output("meoh_syn_cat_in", units="ft**3/yr")
        self.add_output("ng_in", shape=8760, units="kg/h")
        self.add_output("carbon_dioxide_in", shape=8760, units="kg/h")
        self.add_output("electricity_in", shape=8760, units="kW*h/h")

    def size(self):
        self.config = CO2HPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        # Figure out size of plant needed for certain h2 consumption/meoh flow
        cap_factor = self.config.capacity_factor
        h2_meoh_ratio = self.config.h2_consume_ratio
        if self.config.plant_capacity_flow == "hydrogen":
            h2_kgpy = self.config.plant_capacity_kgpy
            hydrogen_kgpy_required = h2_kgpy / h2_meoh_ratio
        elif self.config.plant_capacity_flow == "methanol":
            meoh_kgpy = self.config.plant_capacity_kgpy
            hydrogen_kgpy_required = meoh_kgpy * h2_meoh_ratio * cap_factor

        return hydrogen_kgpy_required

    def compute(self, inputs, outputs):
        # Calculate methanol production from hydrogen in
        h2_kgph = inputs["hydrogen_in"] * 3600
        meoh_kgph = h2_kgph / inputs["h2_consume_ratio"]

        # Parse outputs
        outputs["methanol_out"] = meoh_kgph
        outputs["co2e_emissions"] = meoh_kgph * inputs["co2e_emit_ratio"]
        outputs["h2o_consumption"] = meoh_kgph * inputs["h2o_consume_ratio"]
        outputs["meoh_syn_cat_in"] = np.sum(meoh_kgph) * inputs["meoh_syn_cat_consume_ratio"]
        outputs["ng_in"] = meoh_kgph * inputs["ng_consume_ratio"]
        outputs["carbon_dioxide_in"] = meoh_kgph * inputs["co2_consume_ratio"]
        outputs["electricity_in"] = meoh_kgph * inputs["elec_consume_ratio"]


@define
class CO2HCostConfig(MethanolCostConfig):
    ng_lhv: float = field()
    meoh_syn_cat_price: float = field()
    ng_price: float = field()
    co2_price: float = field()


class CO2HMethanolPlantCostModel(MethanolCostBaseClass):
    """
    An OpenMDAO component for modeling the cost of a CO2 hydrogenation (CO2H) methanol plant.

    Inputs:
        ng_lhv: natural gas lower heating value in MJ/kg
        meoh_syn_cat_consumption: annual consumption of methanol synthesis catalyst (ft**3/yr)
        ng_consumption: hourly consumption of NG (kg/h)
        carbon_dioxide: hourly consumption of CO2 (kg/h)
        electricity: hourly electricity consumption (kW*h/h)
        meoh_syn_cat_price: price of methanol synthesis catalyst (USD/ft**3)
        ng_price: price of NG (USD/MBtu)
        co2_price: price of CO2 (USD/kg)
    Outputs:
        meoh_syn_cat_cost: annual cost of methanol synthesis catalyst (USD/year)
        ng_cost: annual cost of NG (USD/year)
        co2_cost: annual cost of CO2 (USD/year)
    """

    def setup(self):
        self.config = CO2HCostConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()

        self.add_input("ng_lhv", units="MJ/kg", val=self.config.ng_lhv)
        self.add_input("meoh_syn_cat_in", units="ft**3/yr")
        self.add_input("ng_in", shape=8760, units="kg/h")
        self.add_input("carbon_dioxide_in", shape=8760, units="kg/h")
        self.add_input("electricity_in", shape=8760, units="kW*h/h")
        self.add_input("meoh_syn_cat_price", units="USD/ft**3", val=self.config.meoh_syn_cat_price)
        self.add_input(
            "ng_price", units="USD/MBtu", val=self.config.ng_price
        )  # TODO: get OpenMDAO to recognize 'MMBtu'
        self.add_input("co2_price", units="USD/kg", val=self.config.co2_price)

        self.add_output("meoh_syn_cat_cost", units="USD/year")
        self.add_output("ng_cost", units="USD/year")
        self.add_output("co2_cost", units="USD/year")

    def compute(self, inputs, outputs):
        toc_usd = inputs["plant_capacity_kgpy"] * inputs["toc_kg_y"]
        foc_usd_y = inputs["plant_capacity_kgpy"] * inputs["foc_kg_y2"]
        voc_usd_y = np.sum(inputs["methanol_out"]) * inputs["voc_kg"]

        lhv_mj = inputs["ng_lhv"]
        lhv_mmbtu = convert_units(lhv_mj, "MJ", "MBtu")

        outputs["CapEx"] = toc_usd
        outputs["OpEx"] = foc_usd_y + voc_usd_y
        outputs["Fixed_OpEx"] = foc_usd_y
        outputs["Variable_OpEx"] = voc_usd_y
        outputs["meoh_syn_cat_cost"] = inputs["meoh_syn_cat_in"] * inputs["meoh_syn_cat_price"]
        outputs["ng_cost"] = np.sum(inputs["ng_in"]) * lhv_mmbtu * inputs["ng_price"]
        outputs["co2_cost"] = np.sum(inputs["carbon_dioxide_in"]) * inputs["co2_price"]


class CO2HMethanolPlantFinanceModel(MethanolFinanceBaseClass):
    """
    An OpenMDAO component for modeling the financing of a CO2 Hydrogenation (CO2H) methanol plant.

    Inputs:
        meoh_syn_cat_cost: annual cost of synthesis catalyst in USD/year
        ng_cost: annual cost of natural gas in USD/year
        co2_cost: annual cost of CO2 in USD/year
        LCOE: levelized cost of electricity in USD/kWh
        LCOH: levelized cost of hydrogen in USD/kg
    Outputs:
        LCOM_meoh_atr_cat: levelized cost of methanol from ATR catalyst in USD/kg
        LCOM_meoh_syn_cat: levelized cost of methanol from synthesis catalyst in USD/kg
        LCOM_ng: levelized cost of methanol from natural gas in USD/kg
        LCOM_elec: levelized cost of methanol from electricity revenue in USD/kg
    """

    def setup(self):
        self.config = MethanolFinanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "finance")
        )
        super().setup()

        self.add_input(
            "meoh_syn_cat_cost",
            units="USD/year",
            desc="Annual cost of synthesis catalyst in USD/year",
        )
        self.add_input(
            "ng_cost",
            units="USD/year",
            desc="Annual cost of natural gas in USD/year",
        )
        self.add_input(
            "co2_cost",
            units="USD/year",
            desc="Annual cost of carbon dioxide in USD/year",
        )
        self.add_input(
            "electricity_in",
            units="kW*h/h",
            desc="Electricity consumption in kWh/h",
            shape_by_conn=True,
        )
        self.add_input(
            "hydrogen_in",
            units="kg/h",
            desc="Hydrogen consumption in kg/h",
            shape_by_conn=True,
        )
        self.add_input(
            "LCOE",
            units="USD/kW/h",
            desc="Levelized cost of electricity in USD/kWh",
        )
        self.add_input(
            "LCOH",
            units="USD/kg",
            desc="Levelized cost of hydrogen in USD/kg",
        )
        self.add_output(
            "LCOM_meoh_syn_cat",
            units="USD/kg",
            desc="Levelized cost of methanol from synthesis catalyst in USD/kg",
        )
        self.add_output(
            "LCOM_ng",
            units="USD/kg",
            desc="Levelized cost of methanol from natural gas in USD/kg",
        )
        self.add_output(
            "LCOM_co2",
            units="USD/kg",
            desc="Levelized cost of methanol from CO2 in USD/kg",
        )
        self.add_output(
            "LCOM_elec",
            units="USD/kg",
            desc="Levelized cost of methanol from electricity in USD/kWh",
        )
        self.add_output(
            "LCOM_h2",
            units="USD/kg",
            desc="Levelized cost of methanol from hydrogen in USD/kWh",
        )

    def compute(self, inputs, outputs):
        kgph = inputs["methanol_out"]

        lcoe = inputs["LCOE"]
        elec = inputs["electricity_in"]
        elec_cost = lcoe * np.sum(elec)
        lcom_elec = elec_cost / np.sum(kgph)
        outputs["LCOM_elec"] = lcom_elec

        lcoh = inputs["LCOH"]
        h2 = inputs["hydrogen_in"]
        h2_cost = lcoh * np.sum(h2)
        lcom_h2 = h2_cost / np.sum(kgph)
        outputs["LCOM_h2"] = lcom_h2

        lcom_capex = (
            inputs["CapEx"]
            * inputs["fixed_charge_rate"]
            * inputs["tasc_toc_multiplier"]
            / np.sum(kgph)
        )
        lcom_fopex = inputs["Fixed_OpEx"] / np.sum(kgph)
        lcom_vopex = inputs["Variable_OpEx"] / np.sum(kgph)
        outputs["LCOM_meoh_capex"] = lcom_capex
        outputs["LCOM_meoh_fopex"] = lcom_fopex

        meoh_syn_cat_cost = inputs["meoh_syn_cat_cost"]
        lcom_meoh_syn_cat = meoh_syn_cat_cost / np.sum(kgph)
        outputs["LCOM_meoh_syn_cat"] = lcom_meoh_syn_cat

        # Correct LCOM_meoh_vopex which initially included catalyst
        lcom_vopex -= lcom_meoh_syn_cat
        outputs["LCOM_meoh_vopex"] = lcom_vopex

        ng_cost = inputs["ng_cost"]
        lcom_ng = ng_cost / np.sum(kgph)
        outputs["LCOM_ng"] = lcom_ng

        co2_cost = inputs["co2_cost"]
        lcom_co2 = co2_cost / np.sum(kgph)
        outputs["LCOM_co2"] = lcom_co2

        lcom_meoh = lcom_capex + lcom_fopex + lcom_vopex + lcom_meoh_syn_cat
        outputs["LCOM_meoh"] = lcom_meoh

        lcom = lcom_meoh + lcom_ng + lcom_elec + lcom_h2 + lcom_co2
        outputs["LCOM"] = lcom
