from copy import deepcopy
from pathlib import Path

import yaml
import numpy as np
import pytest
import openmdao.api as om
from openmdao.utils.assert_utils import assert_check_totals

from h2integrate.core.h2integrate_model import H2IntegrateModel
from h2integrate.control.control_strategies.openloop_controllers import (
    DemandOpenLoopController,
    PassThroughOpenLoopController,
)


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


def test_demand_controller(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the configuration files
    tech_config_path = current_dir / "inputs" / "tech_config.yaml"

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    tech_config["technologies"]["h2_storage"]["control_strategy"]["model"] = (
        "demand_openloop_controller"
    )
    tech_config["technologies"]["h2_storage"]["model_inputs"]["control_parameters"] = {
        "resource_name": "hydrogen",
        "resource_rate_units": "kg/h",
        "max_capacity": 10.0,  # kg
        "max_charge_percent": 1.0,  # percent as decimal
        "min_charge_percent": 0.0,  # percent as decimal
        "init_charge_percent": 1.0,  # percent as decimal
        "max_charge_rate": 1.0,  # kg/time step
        "max_discharge_rate": 0.5,  # kg/time step
        "charge_efficiency": 1.0,
        "discharge_efficiency": 1.0,
        "demand_profile": [1.0] * 10,  # Example: 10 time steps with 10 kg/time step demand
        "n_time_steps": 10,
    }

    # Set up the OpenMDAO problem
    prob = om.Problem()

    prob.model.add_subsystem(
        name="IVC",
        subsys=om.IndepVarComp(name="hydrogen_in", val=np.arange(10)),
        promotes=["*"],
    )

    prob.model.add_subsystem(
        "demand_openloop_controller",
        DemandOpenLoopController(
            plant_config={}, tech_config=tech_config["technologies"]["h2_storage"]
        ),
        promotes=["*"],
    )

    prob.setup()

    prob.run_model()

    # Run the test
    with subtests.test("Check output"):
        assert pytest.approx([0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "hydrogen_out"
        )

    with subtests.test("Check curtailment"):
        assert pytest.approx([0.0, 0.0, 0.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]) == prob.get_val(
            "hydrogen_curtailed"
        )

    with subtests.test("Check soc"):
        assert pytest.approx([0.95, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "hydrogen_soc"
        )

    with subtests.test("Check missed load"):
        assert pytest.approx([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) == prob.get_val(
            "hydrogen_missed_load"
        )


def test_pyomo_controller(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the input files
    input_path = current_dir / "inputs" / "pyomo_controller" / "h2i_wind_to_h2_storage.yaml"

    model = H2IntegrateModel(input_path)

    model.run()

    prob = model.prob

    # Run the test
    with subtests.test("Check output"):
        assert pytest.approx([0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "h2_storage.hydrogen_out"
        )

    with subtests.test("Check curtailment"):
        assert pytest.approx([0.0, 0.0, 0.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]) == prob.get_val(
            "h2_storage.hydrogen_curtailed"
        )

    with subtests.test("Check soc"):
        assert pytest.approx([0.95, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]) == prob.get_val(
            "h2_storage.hydrogen_soc"
        )

    with subtests.test("Check missed load"):
        assert pytest.approx([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) == prob.get_val(
            "h2_storage.hydrogen_missed_load"
        )


def test_demand_controller_round_trip_efficiency(subtests):
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Resolve the paths to the configuration files
    tech_config_path = current_dir / "inputs" / "tech_config.yaml"

    # Load the technology configuration
    with tech_config_path.open() as file:
        tech_config = yaml.safe_load(file)

    tech_config["technologies"]["h2_storage"]["control_strategy"]["model"] = (
        "demand_openloop_controller"
    )
    tech_config["technologies"]["h2_storage"]["model_inputs"]["control_parameters"] = {
        "resource_name": "hydrogen",
        "resource_rate_units": "kg/h",
        "max_capacity": 10.0,  # kg
        "max_charge_percent": 1.0,  # percent as decimal
        "min_charge_percent": 0.0,  # percent as decimal
        "init_charge_percent": 1.0,  # percent as decimal
        "max_charge_rate": 1.0,  # kg/time step
        "max_discharge_rate": 0.5,  # kg/time step
        "charge_efficiency": 1.0,
        "discharge_efficiency": 1.0,
        "demand_profile": [1.0] * 10,  # Example: 10 time steps with 10 kg/time step demand
        "n_time_steps": 10,
    }

    tech_config_rte = deepcopy(tech_config)
    tech_config_rte["technologies"]["h2_storage"]["model_inputs"]["control_parameters"] = {
        "resource_name": "hydrogen",
        "resource_rate_units": "kg/h",
        "max_capacity": 10.0,  # kg
        "max_charge_percent": 1.0,  # percent as decimal
        "min_charge_percent": 0.0,  # percent as decimal
        "init_charge_percent": 1.0,  # percent as decimal
        "max_charge_rate": 1.0,  # kg/time step
        "max_discharge_rate": 0.5,  # kg/time step
        "round_trip_efficiency": 1.0,
        "demand_profile": [1.0] * 10,  # Example: 10 time steps with 10 kg/time step demand
        "n_time_steps": 10,
    }

    def set_up_and_run_problem(config):
        # Set up the OpenMDAO problem
        prob = om.Problem()

        prob.model.add_subsystem(
            name="IVC",
            subsys=om.IndepVarComp(name="hydrogen_in", val=np.arange(10)),
            promotes=["*"],
        )

        prob.model.add_subsystem(
            "demand_openloop_controller",
            DemandOpenLoopController(
                plant_config={}, tech_config=config["technologies"]["h2_storage"]
            ),
            promotes=["*"],
        )

        prob.setup()

        prob.run_model()

        return prob

    prob_ioe = set_up_and_run_problem(tech_config)
    prob_rte = set_up_and_run_problem(tech_config_rte)

    # Run the test
    with subtests.test("Check output"):
        assert pytest.approx(prob_ioe.get_val("hydrogen_out")) == prob_rte.get_val("hydrogen_out")

    with subtests.test("Check curtailment"):
        assert pytest.approx(prob_ioe.get_val("hydrogen_curtailed")) == prob_rte.get_val(
            "hydrogen_curtailed"
        )

    with subtests.test("Check soc"):
        assert pytest.approx(prob_ioe.get_val("hydrogen_soc")) == prob_rte.get_val("hydrogen_soc")

    with subtests.test("Check missed load"):
        assert pytest.approx(prob_ioe.get_val("hydrogen_missed_load")) == prob_rte.get_val(
            "hydrogen_missed_load"
        )
