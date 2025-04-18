from __future__ import annotations

import numpy as np
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class SMRMethanolBaseClass(BaseConfig):
    """
    A base class used to further define Performance, Cost, and Finacnce classes for a
    Steam Methane Reforming (SMR) methanol plant. Builds on converters.methanol.methanol_baseclass

    Attributes:
        - dec_table_inputs (list of lists):
            Formatted table of inputs/outputs to declare using the "declare_from_table" method
            See examples below - first row is column headers, following rows are inputs/outputs
        - values (dict): key-value pairs to go with dec_table_inputs, in which
            keys: Names of variables to assign values to
            values: Values to assign
            Values do not have to be given for every input/output in dec_table_inputs,
            they will be assigned a value of zero if they are not included in values
    """

    dec_table_inputs: list = field()
    values: dict


@define
class Performance(SMRMethanolBaseClass):
    """
    Defines computation and adds additional inputs/outputs onto MethanolPerformanceBaseClass
    Uses the same XXX_<produce/consume/emit>_ratio and XXX_<production/consumption/emissions>
    structure as MethanolPerformanceBaseClass

    New flows:
        meoh_syn_cat: methanol synthesis catalyst
        meoh_atr_cat: natural gas autothermal reformer catalyst
        lng: liquified natural gas (feedstock)
        elec: electricity (co-product)
    """

    def __init__(
        self,
    ):
        # Additional inputs/outputs to be declared in addition to those already in baseclass
        self.dec_table_inputs = [
            ["type", "len", "conn", "unit", "name"],
            ["in", 1, False, "ft**3/kg", "meoh_syn_cat_consume_ratio"],
            ["in", 1, False, "ft**3/kg", "meoh_atr_cat_consume_ratio"],
            ["in", 1, False, "kg/kg", "lng_consume_ratio"],
            ["in", 1, False, "kW*h/kg", "elec_produce_ratio"],
            ["out", 1, False, "ft**3/yr", "meoh_syn_cat_consumption"],
            ["out", 1, False, "ft**3/yr", "meoh_atr_cat_consumption"],
            ["out", 8760, False, "kg/h", "lng_consumption"],
            ["out", 8760, False, "kW*h/h", "elec_production"],
        ]
        # Values to assign for SMR
        self.values = {
            # Already declared in baseclass
            "co2e_emit_ratio": 1.13442,
            "h2o_consume_ratio": 2.669877132,
            "h2_consume_ratio": 0.0,
            "co2_consume_ratio": 0.0,
            "elec_consume_ratio": 0.1,
            # tech-specific
            "meoh_syn_cat_consume_ratio": 0.00000036322492251,
            "meoh_atr_cat_consume_ratio": 0.0000013078433938,
            "lng_consume_ratio": 1.61561859,
            "elec_produce_ratio": 0.338415339,
        }

    def run_performance_model(self, inputs: dict):
        """
        Calculates flows based off of capacity factor and production/consumption/emission ratios
        """

        # Get plant sizing from config
        cap = inputs["plant_capacity_kgpy"]
        cap_fac = inputs["capacity_factor"]

        # Calculate methanol prodution #TODO get shape from output shape
        meoh_kgph = cap * cap_fac / 8760 * np.ones(shape=(8760,))

        # Calculate other flows
        co2e_emit = meoh_kgph * inputs["co2e_emit_ratio"]
        h2o_cons = meoh_kgph * inputs["h2o_consume_ratio"]
        h2_cons = meoh_kgph * inputs["h2_consume_ratio"]
        co2_cons = meoh_kgph * inputs["co2_consume_ratio"]
        elec_cons = meoh_kgph * inputs["elec_consume_ratio"]
        meoh_atr_cat_cons = np.sum(meoh_kgph) * inputs["meoh_atr_cat_consume_ratio"]
        meoh_syn_cat_cons = np.sum(meoh_kgph) * inputs["meoh_syn_cat_consume_ratio"]
        lng_cons = meoh_kgph * inputs["lng_consume_ratio"]
        elec_prod = meoh_kgph * inputs["elec_produce_ratio"]

        # Parse outputs
        outputs = {}
        outputs["methanol_production"] = meoh_kgph
        outputs["co2_consumption"] = co2_cons
        outputs["h2o_consumption"] = h2o_cons
        outputs["h2_consumption"] = h2_cons
        outputs["co2e_emissions"] = co2e_emit
        outputs["elec_consumption"] = elec_cons
        outputs["meoh_atr_cat_consumption"] = meoh_atr_cat_cons
        outputs["meoh_syn_cat_consumption"] = meoh_syn_cat_cons
        outputs["lng_consumption"] = lng_cons
        outputs["elec_production"] = elec_prod

        return outputs


class Cost(SMRMethanolBaseClass):
    """
    Defines computation and adds additional inputs/outputs onto MethanolCostBaseClass
    Uses the same XXX_<production/consumption/price> and XXX_<cost/revenue> structure as
    MethanolCostBaseClass

    New flows:
        meoh_syn_cat: methanol synthesis catalyst
        meoh_atr_cat: natural gas autothermal reformer catalyst
        lng: liquified natural gas (feedstock)
        elec: electricity (co-product)
    """

    def __init__(
        self,
    ):
        self.dec_table_inputs = [
            ["type", "len", "conn", "unit", "name"],
            ["in", 1, False, "ft**3/yr", "meoh_syn_cat_consumption"],
            ["in", 1, False, "ft**3/yr", "meoh_atr_cat_consumption"],
            ["in", 8760, False, "kg/h", "lng_consumption"],
            ["in", 8760, False, "kW*h/h", "elec_production"],
            ["in", 1, False, "USD/ft**3", "meoh_syn_cat_price"],
            ["in", 1, False, "USD/ft**3", "meoh_atr_cat_price"],
            ["in", 1, False, "USD/MBtu", "lng_price"],  # TODO: get OpenMDAO to recognize 'MMBtu'
            ["in", 1, False, "USD/kW/h", "elec_sales_price"],
            ["out", 1, False, "USD/year", "meoh_syn_cat_cost"],
            ["out", 1, False, "USD/year", "meoh_atr_cat_cost"],
            ["out", 1, False, "USD/year", "lng_cost"],
            ["out", 1, False, "USD/year", "elec_revenue"],
        ]
        self.values = {
            # Already declared in baseclass
            "toc_kg_y": 0.782749307,
            "foc_kg_y^2": 0.020675078,
            "voc_kg": 0.012271827,
            # tech-specific
            "meoh_syn_cat_price": 615.274273,
            "meoh_atr_cat_price": 747.9768786,
            "lng_price": 4.0,
            "elec_sales_price": 0.027498168,
        }

    def run_cost_model(self, inputs: dict):
        """
        Calculates costs based off of cost slopes, prices and production/consumption rates
        """

        MMBTU_per_GJ = 1.055
        LHV = 0.0201  # GJ/kg

        cap = inputs["plant_capacity_kgpy"]
        meoh_kgph = inputs["methanol_production"]

        meoh_syn_cat_price = inputs["meoh_syn_cat_price"]
        meoh_atr_cat_price = inputs["meoh_atr_cat_price"]
        lng_price = inputs["lng_price"]
        elec_sales_price = inputs["elec_sales_price"]

        meoh_atr_cat_cfpy = inputs["meoh_atr_cat_consumption"]
        meoh_syn_cat_cfpy = inputs["meoh_syn_cat_consumption"]
        lng_kgph = inputs["lng_consumption"]
        elec_kwhph = inputs["elec_production"]

        toc_usd = cap * inputs["toc_kg_y"]
        foc_usd_y = cap * inputs["foc_kg_y^2"]
        voc_usd_y = np.sum(meoh_kgph) * inputs["voc_kg"]

        meoh_syn_cat_cost = meoh_syn_cat_cfpy * meoh_syn_cat_price
        meoh_atr_cat_cost = meoh_atr_cat_cfpy * meoh_atr_cat_price
        lng_cost = np.sum(lng_kgph) * MMBTU_per_GJ * LHV * lng_price
        elec_rev = np.sum(elec_kwhph) * elec_sales_price

        outputs = {}

        outputs["CapEx"] = toc_usd
        outputs["OpEx"] = foc_usd_y + voc_usd_y
        outputs["Fixed_OpEx"] = foc_usd_y
        outputs["Variable_OpEx"] = voc_usd_y
        outputs["meoh_syn_cat_cost"] = meoh_syn_cat_cost
        outputs["meoh_atr_cat_cost"] = meoh_atr_cat_cost
        outputs["lng_cost"] = lng_cost
        outputs["elec_revenue"] = elec_rev

        return outputs


class Finance(SMRMethanolBaseClass):
    """
    Defines computation and adds additional inputs/outputs onto MethanolCostBaseClass
    Uses the same <component>_<cost/revenue> LCOM_<component> structure as MethanolCostBaseClass

    meoh_syn_cat are considered part of the methanol plant and included in its lcom_meoh.
    lng and elec are not.
    """

    def __init__(
        self,
    ):
        self.dec_table_inputs = [
            ["type", "len", "conn", "unit", "name"],
            ["in", 1, False, "USD/year", "meoh_syn_cat_cost"],
            ["in", 1, False, "USD/year", "meoh_atr_cat_cost"],
            ["in", 1, False, "USD/year", "lng_cost"],
            ["in", 1, False, "USD/year", "elec_revenue"],
            ["out", 1, False, "USD/kg", "LCOM_meoh_atr_cat"],
            ["out", 1, False, "USD/kg", "LCOM_meoh_syn_cat"],
            ["out", 1, False, "USD/kg", "LCOM_ng"],
            ["out", 1, False, "USD/kg", "LCOM_elec"],
        ]
        self.values = {}

    def run_finance_model(self, inputs):
        """
        Simple financial model of an SMR methanol plant.

        Uses NETL power plant quality guidelines' fixed charge rate method.
        NETL-PUB-22580 doi.org/10.2172/1567736

        """
        toc = inputs["CapEx"]
        fopex = inputs["Fixed_OpEx"]
        vopex = inputs["Variable_OpEx"]
        fcr = inputs["fixed_charge_rate"]
        tasc_toc = inputs["tasc_toc_multiplier"]
        kgph = inputs["methanol_production"]

        outputs = {}

        lcom_capex = toc * fcr * tasc_toc / np.sum(kgph)
        lcom_fopex = fopex / np.sum(kgph)
        lcom_vopex = vopex / np.sum(kgph)
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

        return outputs
