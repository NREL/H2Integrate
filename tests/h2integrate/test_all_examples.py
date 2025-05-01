import os
from pathlib import Path

import pytest

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
        assert pytest.approx(model.prob.get_val("financials_group_1.LCOH"), rel=1e-3) == 7.47944016

    with subtests.test("Check LCOS"):
        assert pytest.approx(model.prob.get_val("steel.LCOS"), rel=1e-3) == 1213.87728644

    with subtests.test("Check total adjusted CapEx"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_1.total_capex_adjusted"), rel=1e-3)
            == 5.10869916e09
        )

    with subtests.test("Check total adjusted OpEx"):
        assert (
            pytest.approx(model.prob.get_val("financials_group_1.total_opex_adjusted"), rel=1e-3)
            == 96349901.77625626
        )

    with subtests.test("Check steel CapEx"):
        assert pytest.approx(model.prob.get_val("steel.CapEx"), rel=1e-3) == 5.78060014e08

    with subtests.test("Check steel OpEx"):
        assert pytest.approx(model.prob.get_val("steel.OpEx"), rel=1e-3) == 1.0129052e08


def test_ammonia_example(subtests):
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
        assert (
            pytest.approx(
                model.prob.get_val("plant.electrolyzer.eco_pem_electrolyzer_cost.CapEx"), rel=1e-3
            )
            == 6.00412524e08
        )

    with subtests.test("Check electrolyzer OpEx"):
        assert (
            pytest.approx(
                model.prob.get_val("plant.electrolyzer.eco_pem_electrolyzer_cost.OpEx"), rel=1e-3
            )
            == 14703155.39207595
        )

    with subtests.test("Check H2 storage CapEx"):
        assert (
            pytest.approx(model.prob.get_val("plant.h2_storage.h2_storage.CapEx"), rel=1e-3)
            == 65645817.61620798
        )

    with subtests.test("Check H2 storage OpEx"):
        assert (
            pytest.approx(model.prob.get_val("plant.h2_storage.h2_storage.OpEx"), rel=1e-3)
            == 2368353.86994941
        )

    with subtests.test("Check ammonia CapEx"):
        assert (
            pytest.approx(model.prob.get_val("plant.ammonia.ammonia_cost.CapEx"), rel=1e-3)
            == 1.0124126e08
        )

    with subtests.test("Check ammonia OpEx"):
        assert (
            pytest.approx(model.prob.get_val("plant.ammonia.ammonia_cost.OpEx"), rel=1e-3)
            == 11178036.31197754
        )

    with subtests.test("Check total adjusted CapEx"):
        assert (
            pytest.approx(
                model.prob.get_val("plant.financials_group_1.total_capex_adjusted"), rel=1e-3
            )
            == 2.5775031e09
        )

    with subtests.test("Check total adjusted OpEx"):
        assert (
            pytest.approx(
                model.prob.get_val("plant.financials_group_1.total_opex_adjusted"), rel=1e-3
            )
            == 53172258.6808771
        )

    with subtests.test("Check LCOH"):
        assert (
            pytest.approx(model.prob.get_val("plant.financials_group_1.LCOH"), rel=1e-3)
            == 4.33286562
        )
