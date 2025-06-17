import numpy as np
import pytest
import openmdao.api as om

from h2integrate.converters.ammonia.ammonia_synloop import AmmoniaSynLoopPerformanceModel


def make_synloop_config():
    return {
        "model_inputs": {
            "performance_parameters": {
                "energy_demand": 0.0006,  # MW per kg NH3
                "nitrogen_conversion_rate": 0.82,  # kg N2 per kg NH3
                "hydrogen_conversion_rate": 0.18,  # kg H2 per kg NH3
            }
        }
    }


def test_ammonia_synloop_limiting_cases():
    config = make_synloop_config()
    # Each test is a single array of 3 hours, each with a different limiting case
    # Case 1: N2 limiting
    n2 = np.array([8.2, 20.0, 20.0])  # Only first entry is N2 limiting
    h2 = np.array([10.0, 1.8, 10.0])  # Second entry is H2 limiting
    elec = np.array([0.006, 0.006, 0.003])  # Third entry is electricity limiting

    expected_nh3 = np.array(
        [
            10.0,  # N2 limiting: 8.2/0.82 = 10
            10.0,  # H2 limiting: 1.8/0.18 = 10
            5.0,  # Electricity limiting: 0.003/0.0006 = 5
        ]
    )

    prob = om.Problem()
    comp = AmmoniaSynLoopPerformanceModel(plant_config={}, tech_config=config)
    prob.model.add_subsystem("synloop", comp)
    prob.setup()
    prob.set_val("synloop.hydrogen_in", h2, units="kg/h")
    prob.set_val("synloop.nitrogen_in", n2, units="kg/h")
    prob.set_val("synloop.electricity_in", elec, units="MW")
    prob.run_model()
    nh3 = prob.get_val("synloop.ammonia_out")
    total = prob.get_val("synloop.total_ammonia_produced")

    # Check NH3 output
    assert np.allclose(nh3, expected_nh3, rtol=1e-6)
    assert np.allclose(total, np.sum(expected_nh3), rtol=1e-6)

    # Check unused resources
    # N2 limiting: index 0, H2 limiting: index 1, Electricity limiting: index 2
    assert pytest.approx(prob.get_val("synloop.nitrogen_out")[0], rel=1e-6) == 0.0
    assert pytest.approx(prob.get_val("synloop.hydrogen_out")[1], rel=1e-6) == 0.0
    assert pytest.approx(prob.get_val("synloop.heat_out")[2], rel=1e-6) == 0.0
