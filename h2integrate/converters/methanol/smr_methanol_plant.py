import numpy as np
from attrs import field, define

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
class SMRPerformanceConfig(MethanolPerformanceConfig):
    meoh_syn_cat_consume_ratio: float = field()
    meoh_atr_cat_consume_ratio: float = field()
    lng_consume_ratio: float = field()
    elec_produce_ratio: float = field()


class SMRMethanolPlantPerformanceModel(MethanolPerformanceBaseClass):
    """
    An OpenMDAO component for modeling the performance of a methanol plant.
    Computes annual methanol and co-product production, feedstock consumption, and emissions
    based on plant capacity and capacity factor.

    Inputs:
        - meoh_syn_cat_consume_ratio: ratio of methanol synthesis catalyst consumed to
            kg methanol produced
        - meoh_atr_cat_consume_ratio: ratio of methanol ATR catalyst consumed to
            kg methanol produced
        - lng_consume_ratio: ratio of LNG consumed to kg methanol produced
        - elec_produce_ratio: ratio of electricity produced to kg methanol produced
    Outputs:
        - meoh_syn_cat_consumption: annual consumption of methanol synthesis catalyst (ft**3/yr)
        - meoh_atr_cat_consumption: annual consumption of methanol ATR catalyst (ft**3/yr)
        - lng_consumption: hourly consumption of LNG (kg/h)
        - electricity: hourly electricity consumption (kW*h/h)
    """

    def setup(self):
        self.config = SMRPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        super().setup()

        # Add in tech-specific variables and values
        self.add_input(
            "meoh_syn_cat_consume_ratio",
            units="ft**3/kg",
            val=self.config.meoh_syn_cat_consume_ratio,
        )
        self.add_input(
            "meoh_atr_cat_consume_ratio",
            units="ft**3/kg",
            val=self.config.meoh_atr_cat_consume_ratio,
        )
        self.add_input("lng_consume_ratio", units="kg/kg", val=self.config.lng_consume_ratio)
        self.add_input("elec_produce_ratio", units="kW*h/kg", val=self.config.elec_produce_ratio)

        self.add_output("meoh_syn_cat_consumption", units="ft**3/yr")
        self.add_output("meoh_atr_cat_consumption", units="ft**3/yr")
        self.add_output("lng_consumption", shape=8760, units="kg/h")
        self.add_output("electricity", shape=8760, units="kW*h/h")

    def compute(self, inputs, outputs):
        # Calculate methanol production #TODO get shape from output shape
        meoh_kgph = (
            inputs["plant_capacity_kgpy"]
            * inputs["capacity_factor"]
            / 8760
            * np.ones(shape=(8760,))
        )

        # Parse outputs
        outputs["methanol"] = meoh_kgph
        outputs["co2_consumption"] = meoh_kgph * inputs["co2_consume_ratio"]
        outputs["h2o_consumption"] = meoh_kgph * inputs["h2o_consume_ratio"]
        outputs["h2_consumption"] = meoh_kgph * inputs["h2_consume_ratio"]
        outputs["co2e_emissions"] = meoh_kgph * inputs["co2e_emit_ratio"]
        outputs["elec_consumption"] = meoh_kgph * inputs["elec_consume_ratio"]
        outputs["meoh_atr_cat_consumption"] = (
            np.sum(meoh_kgph) * inputs["meoh_atr_cat_consume_ratio"]
        )
        outputs["meoh_syn_cat_consumption"] = (
            np.sum(meoh_kgph) * inputs["meoh_syn_cat_consume_ratio"]
        )
        outputs["lng_consumption"] = meoh_kgph * inputs["lng_consume_ratio"]
        outputs["electricity"] = meoh_kgph * inputs["elec_produce_ratio"]


@define
class SMRCostConfig(MethanolCostConfig):
    meoh_syn_cat_price: float = field()
    meoh_atr_cat_price: float = field()
    lng_price: float = field()
    elec_sales_price: float = field()


class SMRMethanolPlantCostModel(MethanolCostBaseClass):
    """
    An OpenMDAO component for modeling the cost of an SMR methanol plant.

    Inputs:
        meoh_syn_cat_consumption: annual consumption of methanol synthesis catalyst (ft**3/yr)
        meoh_atr_cat_consumption: annual consumption of methanol ATR catalyst (ft**3/yr)
        lng_consumption: hourly consumption of LNG (kg/h)
        electricity: hourly electricity consumption (kW*h/h)
        meoh_syn_cat_price: price of methanol synthesis catalyst (USD/ft**3)
        meoh_atr_cat_price: price of methanol ATR catalyst (USD/ft**3)
        lng_price: price of LNG (USD/MBtu)
        elec_sales_price: electricity sales price (USD/kW/h)
    Outputs:
        meoh_syn_cat_cost: annual cost of methanol synthesis catalyst (USD/year)
        meoh_atr_cat_cost: annual cost of methanol ATR catalyst (USD/year)
        lng_cost: annual cost of LNG (USD/year)
        elec_revenue: annual revenue from electricity sales (USD/year)
    """

    def setup(self):
        self.config = SMRCostConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()

        self.add_input("meoh_syn_cat_consumption", units="ft**3/yr")
        self.add_input("meoh_atr_cat_consumption", units="ft**3/yr")
        self.add_input("lng_consumption", shape=8760, units="kg/h")
        self.add_input("electricity", shape=8760, units="kW*h/h")
        self.add_input("meoh_syn_cat_price", units="USD/ft**3", val=self.config.meoh_syn_cat_price)
        self.add_input("meoh_atr_cat_price", units="USD/ft**3", val=self.config.meoh_atr_cat_price)
        self.add_input(
            "lng_price", units="USD/MBtu", val=self.config.lng_price
        )  # TODO: get OpenMDAO to recognize 'MMBtu'
        self.add_input("elec_sales_price", units="USD/kW/h", val=self.config.elec_sales_price)

        self.add_output("meoh_syn_cat_cost", units="USD/year")
        self.add_output("meoh_atr_cat_cost", units="USD/year")
        self.add_output("lng_cost", units="USD/year")
        self.add_output("elec_revenue", units="USD/year")

    def compute(self, inputs, outputs):
        MMBTU_per_GJ = 1.055
        LHV = 0.0201  # GJ/kg

        toc_usd = inputs["plant_capacity_kgpy"] * inputs["toc_kg_y"]
        foc_usd_y = inputs["plant_capacity_kgpy"] * inputs["foc_kg_y2"]
        voc_usd_y = np.sum(inputs["methanol"]) * inputs["voc_kg"]

        outputs["CapEx"] = toc_usd
        outputs["OpEx"] = foc_usd_y + voc_usd_y
        outputs["Fixed_OpEx"] = foc_usd_y
        outputs["Variable_OpEx"] = voc_usd_y
        outputs["meoh_syn_cat_cost"] = (
            inputs["meoh_syn_cat_consumption"] * inputs["meoh_syn_cat_price"]
        )
        outputs["meoh_atr_cat_cost"] = (
            inputs["meoh_atr_cat_consumption"] * inputs["meoh_atr_cat_price"]
        )
        outputs["lng_cost"] = (
            np.sum(inputs["lng_consumption"]) * MMBTU_per_GJ * LHV * inputs["lng_price"]
        )
        outputs["elec_revenue"] = np.sum(inputs["electricity"]) * inputs["elec_sales_price"]


class SMRMethanolPlantFinanceModel(MethanolFinanceBaseClass):
    """
    An OpenMDAO component for modeling the financing of a methanol plant.

    Inputs:
        meoh_syn_cat_cost: annual cost of synthesis catalyst in USD/year
        meoh_atr_cat_cost: annual cost of ATR catalyst in USD/year
        lng_cost: annual cost of natural gas in USD/year
        elec_revenue: annual revenue from electricity sales in USD/year
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
            "meoh_atr_cat_cost",
            units="USD/year",
            desc="Annual cost of ATR catalyst in USD/year",
        )
        self.add_input(
            "lng_cost",
            units="USD/year",
            desc="Annual cost of natural gas in USD/year",
        )
        self.add_input(
            "elec_revenue",
            units="USD/year",
            desc="Annual revenue from electricity sales in USD/year",
        )
        self.add_output(
            "LCOM_meoh_atr_cat",
            units="USD/kg",
            desc="Levelized cost of methanol from ATR catalyst in USD/kg",
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
            "LCOM_elec",
            units="USD/kg",
            desc="Levelized cost of methanol from electricity revenue in USD/kg",
        )

    def compute(self, inputs, outputs):
        kgph = inputs["methanol"]

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
        meoh_atr_cat_cost = inputs["meoh_atr_cat_cost"]
        lcom_meoh_syn_cat = meoh_syn_cat_cost / np.sum(kgph)
        lcom_meoh_atr_cat = meoh_atr_cat_cost / np.sum(kgph)
        outputs["LCOM_meoh_syn_cat"] = lcom_meoh_syn_cat
        outputs["LCOM_meoh_atr_cat"] = lcom_meoh_atr_cat

        # Correct LCOM_meoh_vopex which initially included catalyst
        lcom_vopex -= lcom_meoh_syn_cat + lcom_meoh_atr_cat
        outputs["LCOM_meoh_vopex"] = lcom_vopex

        ng_cost = inputs["lng_cost"]
        lcom_ng = ng_cost / np.sum(kgph)
        outputs["LCOM_ng"] = lcom_ng

        elec_rev = inputs["elec_revenue"]
        lcom_elec = -elec_rev / np.sum(kgph)
        outputs["LCOM_elec"] = lcom_elec

        lcom_meoh = lcom_capex + lcom_fopex + lcom_vopex + lcom_meoh_syn_cat + lcom_meoh_atr_cat
        outputs["LCOM_meoh"] = lcom_meoh

        lcom = lcom_meoh + lcom_ng + lcom_elec
        outputs["LCOM"] = lcom
