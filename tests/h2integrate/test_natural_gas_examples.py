import os
from pathlib import Path

import numpy as np
import pytest

from h2integrate import EXAMPLE_DIR
from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_21_solar_battery_grid_example(subtests):
    # NOTE: would be good to compare LCOE against the same example without grid selling
    # and see that LCOE reduces with grid selling
    os.chdir(EXAMPLE_DIR / "21_solar_battery_grid")

    model = H2IntegrateModel(Path.cwd() / "solar_battery_grid.yaml")

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

    with subtests.test("Behavior check electricity finance subgroup AEP against expected"):
        expected_aep = solar_aep + ng_aep
        # NOTE: ideally this would not include the excess power,
        # this will be done in the flexible finance streams PR
        # expected_aep = solar_aep + ng_aep - sum(excess_power)
        assert pytest.approx(elec_fin_subgroup_aep, rel=1e-6) == expected_aep

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
        assert pytest.approx(tot_lcoe, rel=1e-6) == 52.15484


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
        assert pytest.approx(re_npv, rel=1e-3) == -2.96846876

    with subtests.test("Value check: natural gas subgroup LCOE"):
        ng_lcoe = model.prob.get_val("finance_subgroup_natural_gas.LCOE", units="USD/MW/h")[0]
        assert pytest.approx(ng_lcoe, rel=1e-6) == 67.91951

    with subtests.test("Value check: electricity subgroup LCOE"):
        tot_lcoe = model.prob.get_val("finance_subgroup_electricity.LCOE", units="USD/MW/h")[0]
        assert pytest.approx(tot_lcoe, rel=1e-6) == 57.32746
