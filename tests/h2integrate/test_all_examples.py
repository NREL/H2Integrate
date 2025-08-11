import os
import unittest
import importlib
from pathlib import Path

import pytest
import openmdao.api as om

from h2integrate.core.h2integrate_model import H2IntegrateModel


examples_dir = Path(__file__).resolve().parent.parent.parent / "examples/."


def test_steel_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "01_onshore_steel_mn")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "01_onshore_steel_mn.yaml")

    # Run the model
    model.run()

    model.post_process()
    # Subtests for checking specific values
    with subtests.test("Check LCOH"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_default.LCOH"), rel=1e-3)
            == 7.47944016
        )

    with subtests.test("Check LCOS"):
        assert pytest.approx(model.prob.get_val("steel.LCOS"), rel=1e-3) == 1213.87728644

    with subtests.test("Check total adjusted CapEx"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.total_capex_adjusted"), rel=1e-3
            )
            == 5.10869916e09
        )

    with subtests.test("Check total adjusted OpEx"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.total_opex_adjusted"), rel=1e-3
            )
            == 96349901.77625626
        )

    with subtests.test("Check steel CapEx"):
        assert pytest.approx(model.prob.get_val("steel.CapEx"), rel=1e-3) == 5.78060014e08

    with subtests.test("Check steel OpEx"):
        assert pytest.approx(model.prob.get_val("steel.OpEx"), rel=1e-3) == 1.0129052e08


def test_simple_ammonia_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "02_texas_ammonia")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "02_texas_ammonia.yaml")

    # Run the model
    model.run()

    model.post_process()

    # Subtests for checking specific values
    with subtests.test("Check HOPP CapEx"):
        assert pytest.approx(model.prob.get_val("plant.hopp.hopp.CapEx"), rel=1e-3) == 1.75469962e09

    with subtests.test("Check HOPP OpEx"):
        assert pytest.approx(model.prob.get_val("plant.hopp.hopp.OpEx"), rel=1e-3) == 32953490.4

    with subtests.test("Check electrolyzer CapEx"):
        assert pytest.approx(model.prob.get_val("electrolyzer.CapEx"), rel=1e-3) == 6.00412524e08

    with subtests.test("Check electrolyzer OpEx"):
        assert pytest.approx(model.prob.get_val("electrolyzer.OpEx"), rel=1e-3) == 14703155.39207595

    with subtests.test("Check H2 storage CapEx"):
        assert (
            pytest.approx(model.prob.get_val("plant.h2_storage.h2_storage.CapEx"), rel=1e-3)
            == 65336874.189441
        )

    with subtests.test("Check H2 storage OpEx"):
        assert (
            pytest.approx(model.prob.get_val("plant.h2_storage.h2_storage.OpEx"), rel=1e-3)
            == 2358776.66234517
        )

    with subtests.test("Check ammonia CapEx"):
        assert pytest.approx(model.prob.get_val("ammonia.CapEx"), rel=1e-3) == 1.0124126e08

    with subtests.test("Check ammonia OpEx"):
        assert pytest.approx(model.prob.get_val("ammonia.OpEx"), rel=1e-3) == 11178036.31197754

    with subtests.test("Check total adjusted CapEx"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.total_capex_adjusted"), rel=1e-3
            )
            == 2.76180599e09
        )

    with subtests.test("Check total adjusted OpEx"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.total_opex_adjusted"), rel=1e-3
            )
            == 66599592.71371833
        )

    # Currently underestimated compared to the Reference Design Doc
    with subtests.test("Check LCOH"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_default.LCOH"), rel=1e-3)
            == 4.39187968
        )
    # Currently underestimated compared to the Reference Design Doc
    with subtests.test("Check LCOA"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_default.LCOA"), rel=1e-3)
            == 1.06313924
        )


def test_ammonia_synloop_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "12_ammonia_synloop")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "12_ammonia_synloop.yaml")

    # Run the model
    model.run()

    model.post_process()

    # Subtests for checking specific values
    with subtests.test("Check HOPP CapEx"):
        assert pytest.approx(model.prob.get_val("plant.hopp.hopp.CapEx"), rel=1e-6) == 1.75469962e09

    with subtests.test("Check HOPP OpEx"):
        assert pytest.approx(model.prob.get_val("plant.hopp.hopp.OpEx"), rel=1e-6) == 32953490.4

    with subtests.test("Check electrolyzer CapEx"):
        assert pytest.approx(model.prob.get_val("electrolyzer.CapEx"), rel=1e-6) == 6.00412524e08

    with subtests.test("Check electrolyzer OpEx"):
        assert pytest.approx(model.prob.get_val("electrolyzer.OpEx"), rel=1e-6) == 14703155.39207595

    with subtests.test("Check H2 storage CapEx"):
        assert (
            pytest.approx(model.prob.get_val("plant.h2_storage.h2_storage.CapEx"), rel=1e-6)
            == 65337437.18075897
        )

    with subtests.test("Check H2 storage OpEx"):
        assert (
            pytest.approx(model.prob.get_val("plant.h2_storage.h2_storage.OpEx"), rel=1e-6)
            == 2358794.11507603
        )

    with subtests.test("Check ammonia CapEx"):
        assert pytest.approx(model.prob.get_val("ammonia.CapEx"), rel=1e-6) == 1.15173753e09

    with subtests.test("Check ammonia OpEx"):
        assert pytest.approx(model.prob.get_val("ammonia.OpEx"), rel=1e-6) == 25318447.90064406

    with subtests.test("Check total adjusted CapEx"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.total_capex_adjusted"), rel=1e-6
            )
            == 3.83856529e09
        )

    with subtests.test("Check total adjusted OpEx"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.total_opex_adjusted"), rel=1e-6
            )
            == 81093533.8566508
        )

    with subtests.test("Check LCOH"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_default.LCOH"), rel=1e-6)
            == 5.85374921
        )

    with subtests.test("Check LCOA"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_default.LCOA"), rel=1e-6)
            == 1.10368921
        )


def test_smr_methanol_example(subtests):
    # Change the current working directory to the SMR example's directory
    os.chdir(examples_dir / "03_methanol" / "smr")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "03_smr_methanol.yaml")

    # Run the model
    model.run()

    model.post_process()

    # Check levelized cost of methanol (LCOM)
    with subtests.test("Check SMR LCOM"):
        assert pytest.approx(model.prob.get_val("methanol.LCOM"), rel=1e-6) == 0.22116813


def test_co2h_methanol_example(subtests):
    # Change the current working directory to the CO2 Hydrogenation example's directory
    os.chdir(examples_dir / "03_methanol" / "co2_hydrogenation")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "03_co2h_methanol.yaml")

    # Run the model
    model.run()

    model.post_process()

    # Check levelized cost of methanol (LCOM)
    with subtests.test("Check CO2 Hydrogenation LCOM"):
        assert pytest.approx(model.prob.get_val("methanol.LCOM"), rel=1e-6) == 1.38341179


def test_wind_h2_opt_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "05_wind_h2_opt")

    # Run without optimization
    model_init = H2IntegrateModel(Path.cwd() / "wind_plant_electrolyzer0.yaml")

    # Run the model
    model_init.run()

    model_init.post_process()

    annual_h20 = model_init.prob.get_val("electrolyzer.total_hydrogen_produced", units="kg/year")[0]

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "wind_plant_electrolyzer.yaml")

    # Run the model
    model.run()

    model.post_process()

    with subtests.test("Check initial H2 production"):
        assert annual_h20 < (60500000 - 10000)

    with subtests.test("Check LCOE"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_default.LCOE")[0], rel=1e-3)
            == 0.151189
        )

    with subtests.test("Check electrolyzer size"):
        assert (
            pytest.approx(model.prob.get_val("electrolyzer.electrolyzer_size_mw")[0], rel=1e-3)
            == 1500.0
        )
    # Read the resulting SQL file and compare initial and final LCOH values

    sql_path = None
    for root, _dirs, files in os.walk(Path.cwd()):
        for file in files:
            if file == "wind_h2_opt.sql":
                sql_path = Path(root) / file
                break
        if sql_path:
            break
    assert (
        sql_path is not None
    ), "wind_h2_opt.sql file not found in current working directory or subdirectories."

    cr = om.CaseReader(str(sql_path))
    cases = list(cr.get_cases())
    assert len(cases) > 1, "Not enough cases recorded in SQL file."

    # Get initial and final LCOH values
    initial_lcoh = cases[0].outputs["financials_group_default.LCOH"][0]
    final_lcoh = cases[-1].outputs["financials_group_default.LCOH"][0]

    with subtests.test("Check LCOH changed"):
        assert final_lcoh != initial_lcoh

    with subtests.test("Check total adjusted CapEx"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.total_capex_adjusted")[0], rel=1e-3
            )
            == 2783126102
        )
    with subtests.test("Check total adjusted OpEx"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.total_opex_adjusted")[0], rel=1e-3
            )
            == 75543899
        )

    with subtests.test("Check minimum total hydrogen produced"):
        assert (
            pytest.approx(
                model.prob.get_val("electrolyzer.total_hydrogen_produced", units="kg/year")[0],
                abs=10000,
            )
            == 60500000
        )


def test_paper_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "06_custom_tech")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "wind_plant_paper.yaml")

    # Run the model
    model.run()

    model.post_process()

    # Subtests for checking specific values
    with subtests.test("Check LCOP"):
        assert (
            pytest.approx(
                model.prob.get_val("plant.paper_mill.paper_mill_financial.LCOP"), rel=1e-3
            )
            == 51.91476681
        )


@unittest.skipUnless(importlib.util.find_spec("mcm") is not None, "mcm is not installed")
def test_wind_wave_doc_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "09_wind_wave_doc")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "offshore_plant_doc.yaml")

    # Run the model
    model.run()

    model.post_process()

    # Subtests for checking specific values
    with subtests.test("Check LCOC"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_default.LCOC"), rel=1e-3)
            == 2.26955589
        )

    with subtests.test("Check LCOE"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_default.LCOE"), rel=1e-3)
            == 1.05281478
        )


def test_hydro_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "07_run_of_river_plant")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "07_run_of_river.yaml")

    # Run the model
    model.run()

    model.post_process()

    print(model.prob.get_val("financials_group_default.LCOE"))

    # Subtests for checking specific values
    with subtests.test("Check LCOE"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_default.LCOE"), rel=1e-3)
            == 0.17653979
        )


def test_hybrid_energy_plant_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "11_hybrid_energy_plant")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "wind_pv_battery.yaml")

    # Run the model
    model.run()

    model.post_process()

    # Subtests for checking specific values
    with subtests.test("Check LCOE"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.LCOE", units="USD/MW/h")[0],
                rel=1e-5,
            )
            == 83.2123
        )


def test_asu_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "13_air_separator")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "13_air_separator.yaml")

    # Run the model
    model.run()

    model.post_process()

    # Subtests for checking specific values
    with subtests.test("Check LCON"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.LCON", units="USD/kg")[0],
                abs=1e-4,
            )
            == 0.28694531
        )


def test_hydrogen_dispatch_example(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "14_wind_hydrogen_dispatch")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "inputs" / "h2i_wind_to_h2_storage.yaml")

    model.run()

    model.post_process()

    with subtests.test("Check LCOE"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.LCOE", units="USD/MW/h")[0],
                rel=1e-5,
            )
            == 106.13987
        )

    with subtests.test("Check LCOH"):
        assert (
            pytest.approx(
                model.prob.get_val("financials_group_default.LCOH", units="USD/kg")[0],
                rel=1e-5,
            )
            == 5.68452215
        )
