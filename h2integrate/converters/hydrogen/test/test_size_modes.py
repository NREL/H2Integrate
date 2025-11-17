import os
from pathlib import Path

import pytest

from h2integrate import EXAMPLE_DIR
from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_resize_by_max_feedstock(subtests):
    # Change the current working directory to the example's directory
    os.chdir(EXAMPLE_DIR / "22_sizing_modes")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "22_size_mode_feedstock.yaml")

    model.run()
    model.post_process()

    with subtests.test("Check electrolyzer feedstock sizing"):
        assert (
            pytest.approx(model.prob.get_val("electrolyzer.electrolyzer_size_mw")[0], rel=1e-3)
            == 1080
        )


def test_resize_by_max_commodity(subtests):
    # Change the current working directory to the example's directory
    os.chdir(EXAMPLE_DIR / "22_sizing_modes")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "22_size_mode_commodity.yaml")

    model.run()
    model.post_process()

    with subtests.test("Check electrolyzer commodity sizing"):
        assert (
            pytest.approx(model.prob.get_val("electrolyzer.electrolyzer_size_mw")[0], rel=1e-3)
            == 560
        )
