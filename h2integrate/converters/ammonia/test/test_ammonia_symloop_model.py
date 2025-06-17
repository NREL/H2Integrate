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


def test_ammonia_synloop_limiting_cases(subtests):
    config = make_synloop_config()
    # Each test is a single hour (shape=1)
    # Case 1: N2 limiting
    n2 = np.array([8.2])  # can make 10 kg NH3 (limiting: 8.2/0.82 = 10)
    h2 = np.array([10.0])  # can make 55.555... kg NH3 (10/0.18)
    elec = np.array([0.006])  # can make 10 kg NH3 (0.006/0.0006)
    # Case 2: H2 limiting
    h2_2 = np.array([1.8])  # can make 10 kg NH3 (limiting: 1.8/0.18 = 10)
    n2_2 = np.array([20.0])  # can make 24.39 kg NH3 (20/0.82)
    elec_2 = np.array([0.006])  # can make 10 kg NH3 (0.006/0.0006)
    # Case 3: Elec limiting
    elec_3 = np.array([0.003])  # can make 5 kg NH3 (limiting: 0.003/0.0006 = 5)
    h2_3 = np.array([10.0])  # can make 55.555... kg NH3
    n2_3 = np.array([20.0])  # can make 24.39 kg NH3
    cases = [
        ("N2 limiting", h2, n2, elec, 10.0),
        ("H2 limiting", h2_2, n2_2, elec_2, 10.0),
        ("Electricity limiting", h2_3, n2_3, elec_3, 5.0),
    ]
    for name, h2_in, n2_in, elec_in, expected_nh3 in cases:
        with subtests.test(name):
            prob = om.Problem()
            comp = AmmoniaSynLoopPerformanceModel(plant_config={}, tech_config=config)
            prob.model.add_subsystem("synloop", comp)
            prob.setup()
            prob.set_val("synloop.hydrogen_in", h2_in, units="kg/h")
            prob.set_val("synloop.nitrogen_in", n2_in, units="kg/h")
            prob.set_val("synloop.electricity_in", elec_in, units="MW")
            prob.run_model()
            nh3 = prob.get_val("synloop.ammonia_out")[0]
            total = prob.get_val("synloop.total_ammonia_produced")
            # Check NH3 output
            assert pytest.approx(nh3, rel=1e-6) == expected_nh3
            assert pytest.approx(total, rel=1e-6) == expected_nh3
            # Check unused resources
            if name == "N2 limiting":
                assert pytest.approx(prob.get_val("synloop.nitrogen_out")[0], rel=1e-6) == 0.0
            elif name == "H2 limiting":
                assert pytest.approx(prob.get_val("synloop.hydrogen_out")[0], rel=1e-6) == 0.0
            elif name == "Electricity limiting":
                assert pytest.approx(prob.get_val("synloop.heat_out")[0], rel=1e-6) == 0.0
