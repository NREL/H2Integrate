import os
from pathlib import Path

import pytest

from h2integrate import EXAMPLE_DIR
from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_resize_by_max_feedstock(subtests):
    # Change the current working directory to the example's directory
    os.chdir(EXAMPLE_DIR / "22_sizing_modes")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "22_size_mode_iterative.yaml")

    model.technology_config["technologies"]["electrolyzer"]["model_inputs"][
        "performance_parameters"
    ]["sizing"] = {
        "size_mode": "resize_by_max_feedstock",
        "flow_used_for_sizing": "electricity",
        "max_feedstock_ratio": 1.0,
    }
    model.setup()

    model.run()
    model.post_process()

    with subtests.test("Check electrolyzer size"):
        assert (
            pytest.approx(model.prob.get_val("electrolyzer.electrolyzer_size_mw")[0], rel=1e-3)
            == 1080
        )


def test_resize_by_max_commodity(subtests):
    # Change the current working directory to the example's directory
    os.chdir(EXAMPLE_DIR / "22_sizing_modes")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "22_size_mode_iterative.yaml")

    model.technology_config["technologies"]["electrolyzer"]["model_inputs"][
        "performance_parameters"
    ]["sizing"] = {
        "size_mode": "resize_by_max_commodity",
        "flow_used_for_sizing": "hydrogen",
        "max_commodity_ratio": 1.0,
    }
    model.setup()

    model.run()
    model.post_process()

    with subtests.test("Check electrolyzer size"):
        assert (
            pytest.approx(model.prob.get_val("electrolyzer.electrolyzer_size_mw")[0], rel=1e-3)
            == 560
        )
