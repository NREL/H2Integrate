import os
from pathlib import Path

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

    electricity_bought = sum(model.prob.get_val("grid_buy.electricity_out", units="kW"))
    battery_missed_load = sum(model.prob.get_val("battery.electricity_unmet_demand", units="kW"))

    battery_curtailed = sum(model.prob.get_val("battery.electricity_unused_commodity", units="kW"))
    electricity_sold = sum(model.prob.get_val("grid_sell.electricity_in", units="kW"))

    solar_aep = sum(model.prob.get_val("solar.electricity_out", units="kW"))

    with subtests.test("Behavior check battery missed load is electricity bought"):
        assert pytest.approx(battery_missed_load, rel=1e-6) == electricity_bought

    with subtests.test("Behavior check battery curtailed energy is electricity sold"):
        assert pytest.approx(battery_curtailed, rel=1e-6) == electricity_sold

    with subtests.test(
        "Behavior check energy for financials; include solar aep and electricity bought"
    ):
        assert pytest.approx(energy_for_financials, rel=1e-6) == (solar_aep + electricity_bought)

    with subtests.test("Value check on LCOE"):
        lcoe = model.prob.get_val("finance_subgroup_renewables.LCOE", units="USD/(MW*h)")[0]
        assert pytest.approx(lcoe, rel=1e-4) == 91.7057887
