import os
from pathlib import Path

import pytest

from h2integrate import EXAMPLE_DIR
from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_size_mode_outputs(subtests):
    # Change the current working directory to the example's directory
    os.chdir(EXAMPLE_DIR / "22_sizing_modes")

    # Create a H2Integrate model
    model = H2IntegrateModel(Path.cwd() / "22_size_mode_iterative.yaml")
    # Subtests for checking specific values
    with subtests.test("Test `resize_by_max_feedstock` mode"):
        model.technology_config["technologies"]["electrolyzer"]["model_inputs"][
            "performance_parameters"
        ]["sizing"] = {
            "size_mode": "resize_by_max_feedstock",
            "resize_by_flow": "electricity",
            "max_feedstock_ratio": 1.0,
        }
        model.setup()

        model.run()
        assert (
            pytest.approx(model.prob.get_val("electrolyzer.electrolyzer_size_mw")[0], rel=1e-3)
            == 1080
        )

    with subtests.test("Test `resize_by_max_commodity` mode"):
        model.technology_config["technologies"]["electrolyzer"]["model_inputs"][
            "performance_parameters"
        ]["sizing"] = {
            "size_mode": "resize_by_max_commodity",
            "resize_by_flow": "hydrogen",
            "max_commodity_ratio": 1.0,
        }
        model.setup()

        model.run()
        assert (
            pytest.approx(model.prob.get_val("electrolyzer.electrolyzer_size_mw")[0], rel=1e-3)
            == 560
        )
