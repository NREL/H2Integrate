from pathlib import Path

import yaml
import numpy as np
import pytest
import openmdao.api as om
from openmdao.utils.assert_utils import assert_check_totals

from h2integrate.controllers.openloop_controllers import PassThroughOpenLoopController


def test_pass_through_controller(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the configuration files
    tech_config_path = current_dir / "inputs" / "tech_config.yaml"

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    # Set up the OpenMDAO problem
    prob = om.Problem()

    prob.model.add_subsystem(
        name="IVC",
        subsys=om.IndepVarComp(name="hydrogen_in", val=np.arange(10)),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        "pass_through_controller",
        PassThroughOpenLoopController(
            plant_config={}, tech_config=tech_config["technologies"]["h2_storage"]
        ),
        promotes=["*"],
    )

    prob.setup()

    prob.run_model()

    # Run the test
    with subtests.test("Check output"):
        assert pytest.approx(prob.get_val("hydrogen_out"), rel=1e-3) == np.arange(10)

    # Run the test
    with subtests.test("Check derivatives"):
        # check total derivatives using OpenMDAO's check_totals and assert tools
        assert_check_totals(
            prob.check_totals(
                of=[
                    "hydrogen_out",
                ],
                wrt=[
                    "hydrogen_in",
                ],
                step=1e-6,
                form="central",
                show_only_incorrect=False,
                out_stream=None,
            )
        )
