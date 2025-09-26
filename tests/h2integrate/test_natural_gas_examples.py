import os
from pathlib import Path

import numpy as np
import pytest

from h2integrate import EXAMPLE_DIR
from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_natural_gas_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(EXAMPLE_DIR / "24_natural_gas_with_commodity_streams")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "natgas.yaml")

    # Run the model

    model.run()

    model.post_process()
    solar_aep = sum(model.prob.get_val("solar.electricity_out", units="kW"))
    solar_bat_out_total = sum(model.prob.get_val("battery.electricity_out", units="kW"))
    solar_curtailed_total = sum(model.prob.get_val("battery.electricity_curtailed", units="kW"))

    renewable_subgroup_total_electricity = model.prob.get_val(
        "finance_subgroup_renewables.electricity_sum.total_electricity_produced", units="kW*h/year"
    )[0]

    # new subgroup to show commodity stream impact
    renewables_used_subgroup_total_electricity = model.prob.get_val(
        "finance_subgroup_renewables_used.electricity_sum.total_electricity_produced",
        units="kW*h/year",
    )[0]

    electricity_subgroup_total_electricity = model.prob.get_val(
        "finance_subgroup_electricity.electricity_sum.total_electricity_produced", units="kW*h/year"
    )[0]
    natural_gas_subgroup_total_electricity = model.prob.get_val(
        "finance_subgroup_natural_gas.electricity_sum.total_electricity_produced", units="kW*h/year"
    )[0]

    # NOTE: battery output power is not included in any of the financial calcs
    # that dont specify commodity stream

    pre_ng_missed_load = model.prob.get_val("battery.electricity_missed_load", units="kW")
    ng_electricity_demand = model.prob.get_val("natural_gas_plant.electricity_demand", units="kW")
    ng_electricity_production = model.prob.get_val("natural_gas_plant.electricity_out", units="kW")
    bat_init_charge = 200000.0 * 0.1  # max capacity in kW and initial charge rate percentage

    with subtests.test(
        "Check solar AEP is greater than battery output (solar oversized relative to demand"
    ):
        assert solar_aep > solar_bat_out_total

    with subtests.test(
        "Check battery outputs against battery inputs (solar oversized relative to demand"
    ):
        assert (
            pytest.approx(solar_bat_out_total + solar_curtailed_total, abs=bat_init_charge)
            == solar_aep
        )

    with subtests.test("Check solar AEP equals total electricity for renewables subgroup"):
        assert pytest.approx(solar_aep, rel=1e-6) == renewable_subgroup_total_electricity

    with subtests.test(
        "Check battery output AEP equals total electricity for renewables used subgroup"
    ):
        assert (
            pytest.approx(solar_bat_out_total, rel=1e-6)
            == renewables_used_subgroup_total_electricity
        )

    with subtests.test("Check natural gas AEP equals total electricity for natural_gas subgroup"):
        assert (
            pytest.approx(sum(ng_electricity_production), rel=1e-6)
            == natural_gas_subgroup_total_electricity
        )

    with subtests.test(
        "Check natural gas + solar AEP equals total electricity for electricity subgroup"
    ):
        assert (
            pytest.approx(electricity_subgroup_total_electricity, rel=1e-6)
            == sum(ng_electricity_production) + solar_aep
        )

    with subtests.test("Check missed load is natural gas plant electricity demand"):
        assert pytest.approx(ng_electricity_demand, rel=1e-6) == pre_ng_missed_load

    with subtests.test("Check natural_gas_plant electricity out equals demand"):
        assert pytest.approx(ng_electricity_demand, rel=1e-6) == ng_electricity_production

    # Subtests for checking specific values
    with subtests.test("Check Natural Gas CapEx"):
        capex = model.prob.get_val("natural_gas_plant.CapEx")[0]
        assert pytest.approx(capex, rel=1e-6) == 1e8

    with subtests.test("Check Natural Gas OpEx"):
        fopex = model.prob.get_val("natural_gas_plant.OpEx")[0]
        vopex = model.prob.get_val("natural_gas_plant.VarOpEx")[0]
        opex = fopex + vopex
        assert pytest.approx(opex, rel=1e-6) == 2243167.245258862

    with subtests.test("Check total electricity produced"):
        assert pytest.approx(natural_gas_subgroup_total_electricity, rel=1e-6) == 497266898.10354495

    with subtests.test("Check opex adjusted ng_feedstock"):
        opex_ng_feedstock = model.prob.get_val(
            "finance_subgroup_natural_gas.varopex_adjusted_ng_feedstock"
        )[0]
        assert pytest.approx(opex_ng_feedstock, rel=1e-6) == 15281860.770986987

    with subtests.test("Check capex adjusted natural_gas_plant"):
        capex_ng_plant = model.prob.get_val(
            "finance_subgroup_natural_gas.capex_adjusted_natural_gas_plant"
        )[0]
        assert pytest.approx(capex_ng_plant, rel=1e-6) == 97560975.60975611

    with subtests.test("Check opex adjusted natural_gas_plant"):
        fopex_ng_plant = model.prob.get_val(
            "finance_subgroup_natural_gas.opex_adjusted_natural_gas_plant"
        )[0]
        vopex_ng_plant = model.prob.get_val(
            "finance_subgroup_natural_gas.varopex_adjusted_natural_gas_plant"
        )[0]
        opex_ng_plant = vopex_ng_plant + fopex_ng_plant
        assert pytest.approx(opex_ng_plant, rel=1e-6) == 2188455.8490330363

    with subtests.test("Check total adjusted CapEx for natural gas subgroup"):
        total_capex = model.prob.get_val("finance_subgroup_natural_gas.total_capex_adjusted")[0]
        assert pytest.approx(total_capex, rel=1e-6) == 97658536.58536586

    with subtests.test("Check total adjusted OpEx for natural gas subgroup"):
        total_fopex = model.prob.get_val("finance_subgroup_natural_gas.total_opex_adjusted")[0]
        total_vopex = model.prob.get_val("finance_subgroup_natural_gas.total_varopex_adjusted")[0]
        total_opex = total_fopex + total_vopex
        assert pytest.approx(total_opex, rel=1e-6) == 17470316.62

    with subtests.test("Check LCOE (natural gas plant)"):
        lcoe_ng = model.prob.get_val("finance_subgroup_natural_gas.LCOE")[0]
        assert pytest.approx(lcoe_ng, rel=1e-6) == 0.05811033466

    with subtests.test("Check LCOE (renewables plant)"):
        lcoe_re = model.prob.get_val("finance_subgroup_renewables.LCOE")[0]
        assert pytest.approx(lcoe_re, rel=1e-6) == 0.07102560120

    with subtests.test("Check LCOE (renewables and natural gas plant)"):
        lcoe_tot = model.prob.get_val("finance_subgroup_electricity.LCOE")[0]
        assert pytest.approx(lcoe_tot, rel=1e-6) == 0.063997927290

    # Test feedstock-specific values
    with subtests.test("Check feedstock output"):
        ng_output = model.prob.get_val("ng_feedstock_source.natural_gas_out")
        # Should be rated capacity (100 MMBtu) for all timesteps
        assert all(ng_output == 750.0)

    with subtests.test("Check feedstock consumption"):
        ng_consumed = model.prob.get_val("ng_feedstock.natural_gas_consumed")
        # Total consumption should match what the natural gas plant uses
        expected_consumption = (
            model.prob.get_val("natural_gas_plant.electricity_out") * 7.5
        )  # Convert MWh to MMBtu using heat rate
        assert pytest.approx(ng_consumed.sum(), rel=1e-3) == expected_consumption.sum()

    with subtests.test("Check feedstock CapEx"):
        ng_capex = model.prob.get_val("ng_feedstock.CapEx")[0]
        assert pytest.approx(ng_capex, rel=1e-6) == 100000.0  # start_up_cost

    with subtests.test("Check feedstock OpEx"):
        ng_opex = model.prob.get_val("ng_feedstock.VarOpEx")[0]
        # OpEx should be annual_cost (0) + price * consumption
        ng_consumed = model.prob.get_val("ng_feedstock.natural_gas_consumed")
        expected_opex = 4.2 * ng_consumed.sum()  # price = 4.2 $/MMBtu
        assert pytest.approx(ng_opex, rel=1e-6) == expected_opex


def test_21_solar_battery_grid_example(subtests):
    # NOTE: would be good to compare LCOE against the same example without grid selling
    # and see that LCOE reduces with grid selling
    os.chdir(EXAMPLE_DIR / "21_solar_battery_grid")

    model = H2IntegrateModel(Path.cwd() / "solar_battery_grid.yaml")

    # Run the model

    model.run()

    model.post_process()

    energy_for_financials = model.prob.get_val(
        "finance_subgroup_renewables.electricity_sum.total_electricity_produced", units="kW*h/year"
    )

    electricity_bought = sum(model.prob.get_val("grid_feedstock.electricity_consumed", units="kW"))
    battery_missed_load = sum(model.prob.get_val("battery.electricity_missed_load", units="kW"))

    battery_curtailed = sum(model.prob.get_val("battery.electricity_curtailed", units="kW"))
    electricity_sold = sum(model.prob.get_val("grid_selling.electricity_sold", units="kW"))

    solar_aep = sum(model.prob.get_val("solar.electricity_out", units="kW"))

    with subtests.test("Behavior check battery missed load is electricity bought"):
        assert pytest.approx(battery_missed_load, rel=1e-6) == electricity_bought

    with subtests.test("Behavior check battery curtailed energy is electricity sold"):
        assert pytest.approx(battery_curtailed, rel=1e-6) == -1 * electricity_sold

    with subtests.test("Behavior check energy for financials it solar aep and electricity bought"):
        # NOTE: ideally this would include energy bought from grid,
        # this will be done in the flexible finance streams PR
        # expected_aep = solar_aep + electricity_bought
        assert pytest.approx(energy_for_financials, rel=1e-6) == solar_aep

    with subtests.test("Value check on LCOE"):
        lcoe = model.prob.get_val("finance_subgroup_renewables.LCOE", units="USD/MW/h")[0]
        assert pytest.approx(lcoe, rel=1e-6) == 66.11939


def test_example_22_solar_ng_generic_load(subtests):
    """Integration test for adding in demand component without battery."""
    os.chdir(EXAMPLE_DIR / "22_solar_ng_demand")

    model = H2IntegrateModel(Path.cwd() / "solar_ng_demand.yaml")

    model.run()

    model.post_process()

    solar_aep = sum(model.prob.get_val("solar.electricity_out", units="kW"))
    ng_aep = sum(model.prob.get_val("natural_gas_plant.electricity_out", units="kW"))
    excess_power = model.prob.get_val("electrical_load_demand.electricity_curtailed", units="kW")
    hourly_demand_kW = 100000.0
    combiner_aep = sum(model.prob.get_val("combiner.electricity_out", units="kW"))

    elec_fin_subgroup_aep = model.prob.get_val(
        "finance_subgroup_electricity.electricity_sum.total_electricity_produced", units="kW*h/year"
    )[0]
    renewable_fin_subgroup_aep = model.prob.get_val(
        "finance_subgroup_renewables.electricity_sum.total_electricity_produced", units="kW*h/year"
    )[0]
    ng_fin_subgroup_aep = model.prob.get_val(
        "finance_subgroup_natural_gas.electricity_sum.total_electricity_produced", units="kW*h/year"
    )[0]
    solar_to_load = np.where(
        model.prob.get_val("solar.electricity_out", units="kW") > hourly_demand_kW,
        hourly_demand_kW,
        model.prob.get_val("solar.electricity_out", units="kW"),
    )

    with subtests.test("Behavior check solar AEP is same as renewables subgroup AEP"):
        assert pytest.approx(renewable_fin_subgroup_aep, rel=1e-6) == solar_aep

    with subtests.test("Behavior check combiner AEP is solar + ng - curtailed"):
        expected_aep = solar_aep + ng_aep - sum(excess_power)

        assert pytest.approx(combiner_aep, rel=1e-6) == expected_aep

    with subtests.test("Behavior check missed load is natural gas demand"):
        assert pytest.approx(
            model.prob.get_val("electrical_load_demand.electricity_missed_load", units="kW"), 1e-6
        ) == model.prob.get_val("natural_gas_plant.electricity_demand", units="kW")

    with subtests.test("Behavior check natural_gas finance subgroup AEP"):
        assert (
            pytest.approx(
                sum(model.prob.get_val("natural_gas_plant.electricity_demand", units="kW")), 1e-6
            )
            == ng_fin_subgroup_aep
        )

    with subtests.test("Behavior check on curtailed energy"):
        solar_excess = np.sum(
            model.prob.get_val("solar.electricity_out", units="kW") - solar_to_load
        )
        assert pytest.approx(np.sum(excess_power), rel=1e-6) == solar_excess

    with subtests.test("Behavior check electricity finance subgroup AEP is from combiner AEP"):
        assert pytest.approx(elec_fin_subgroup_aep, rel=1e-6) == combiner_aep

    with subtests.test("Behavior check electricity out from demand does not exceed demand"):
        assert all(
            model.prob.get_val("electrical_load_demand.electricity_out", units="kW")
            <= hourly_demand_kW
        )

    with subtests.test("Value check: renewables subgroup LCOE"):
        re_lcoe = model.prob.get_val("finance_subgroup_renewables.LCOE", units="USD/MW/h")[0]
        assert pytest.approx(re_lcoe, rel=1e-6) == 49.43456

    with subtests.test("Value check: natural gas subgroup LCOE"):
        ng_lcoe = model.prob.get_val("finance_subgroup_natural_gas.LCOE", units="USD/MW/h")[0]
        assert pytest.approx(ng_lcoe, rel=1e-6) == 54.23308

    with subtests.test("Value check: electricity subgroup LCOE"):
        tot_lcoe = model.prob.get_val("finance_subgroup_electricity.LCOE", units="USD/MW/h")[0]
        assert pytest.approx(tot_lcoe, rel=1e-6) == 57.268770102


def test_example_26_solar_wind_ng_generic_load_example(subtests):
    """Integration test for adding in pysam wind plant model."""
    os.chdir(EXAMPLE_DIR / "26_solar_wind_ng_demand")

    model = H2IntegrateModel(Path.cwd() / "solar_wind_ng_demand.yaml")

    model.run()

    model.post_process()

    solar_aep = sum(model.prob.get_val("solar.electricity_out", units="kW"))
    wind_aep = sum(model.prob.get_val("wind.electricity_out", units="kW"))
    wind_solar_aep = sum(model.prob.get_val("combiner.electricity_out", units="kW"))
    ng_aep = sum(model.prob.get_val("natural_gas_plant.electricity_out", units="kW"))

    with subtests.test("Behavior check on wind and solar to combiner"):
        assert pytest.approx(wind_solar_aep, rel=1e-6) == wind_aep + solar_aep

    with subtests.test("Behavior check missed load is natural gas demand"):
        assert pytest.approx(
            model.prob.get_val("electrical_load_demand.electricity_missed_load", units="kW"), 1e-6
        ) == model.prob.get_val("natural_gas_plant.electricity_demand", units="kW")

    with subtests.test("Value check wind aep"):
        assert pytest.approx(wind_aep, rel=1e-3) == 4.06908034 * 1e8

    with subtests.test("Value check wind capacity"):
        assert (
            pytest.approx(model.prob.get_val("wind.total_capacity", units="MW"), rel=1e-6) == 6 * 20
        )

    with subtests.test("Value check solar aep"):
        assert pytest.approx(solar_aep, rel=1e-3) == 2.08298595 * 1e8

    with subtests.test("Value check natural gas aep"):
        assert pytest.approx(ng_aep, rel=1e-3) == 328566259.35675

    with subtests.test("Value check: renewables subgroup LCOE (ProFastLCO)"):
        re_lcoe = model.prob.get_val(
            "finance_subgroup_renewables.LCOE_profast_lco", units="USD/MW/h"
        )[0]
        assert pytest.approx(re_lcoe, rel=1e-6) == 51.67052

    with subtests.test("Value check: renewables subgroup NPV (ProFastNPV)"):
        re_npv = model.prob.get_val(
            "finance_subgroup_renewables.NPV_electricity_profast_npv", units="USD"
        )
        assert pytest.approx(re_npv, rel=1e-6) == 167369837774.4052

    with subtests.test("Value check: natural gas subgroup LCOE"):
        ng_lcoe = model.prob.get_val("finance_subgroup_natural_gas.LCOE", units="USD/MW/h")[0]
        assert pytest.approx(ng_lcoe, rel=1e-6) == 67.91951

    with subtests.test("Value check: electricity subgroup LCOE"):
        tot_lcoe = model.prob.get_val("finance_subgroup_electricity.LCOE", units="USD/MW/h")[0]
        assert pytest.approx(tot_lcoe, rel=1e-6) == 57.32746
