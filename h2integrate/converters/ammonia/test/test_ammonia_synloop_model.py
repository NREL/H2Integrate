import numpy as np
import pytest
import openmdao.api as om

from h2integrate.converters.ammonia.ammonia_synloop import AmmoniaSynLoopPerformanceModel


def make_synloop_config():
    return {
        "model_inputs": {
            "shared_parameters": {
                "production_capacity": 52777.6,
                "catalyst_consumption_rate": 0.000091295354067341,
                "catalyst_replacement_interval": 3,
            },
            "performance_parameters": {
                "capacity_factor": 0.9,
                "energy_demand": 0.530645243,
                "heat_output": 0.8299956,
                "feed_gas_t": 25.8,
                "feed_gas_p": 20,
                "feed_gas_x_n2": 0.25,
                "feed_gas_x_h2": 0.75,
                "feed_gas_mass_ratio": 1.13,
                "purge_gas_t": 7.5,
                "purge_gas_p": 275,
                "purge_gas_x_n2": 0.26,
                "purge_gas_x_h2": 0.68,
                "purge_gas_x_ar": 0.02,
                "purge_gas_x_nh3": 0.04,
                "purge_gas_mass_ratio": 0.07,
            },
        }
    }


def test_ammonia_synloop_limiting_cases():
    config = make_synloop_config()
    plant_info = {
        "simulation": {
            "n_timesteps": 4,  # Using 4 timesteps for this test
            "dt": 3600,
        }
    }

    # Each test is a single array of 4 hours, each with a different limiting case
    # Case 1: N2 limiting
    cap_mult = 5000
    n2 = np.array([2.0, 5.0, 5.0, 5.0]) * cap_mult  # Only first entry is N2 limiting
    h2 = np.array([2.0, 1.0, 2.0, 2.0]) * cap_mult  # Second entry is H2 limiting
    elec = np.array([0.006, 0.006, 0.003, 0.006]) * cap_mult  # Third entry is electricity limiting
    # Fourth entry is capacity-limited

    expected_nh3 = np.array(
        [
            21520.21334466,  # N2 limiting
            49840.21632252,  # H2 limiting
            28267.47285097,  # Electricity limiting
            52777.6,  # Capacity limiting
        ]
    )

    prob = om.Problem()
    comp = AmmoniaSynLoopPerformanceModel(plant_config={"plant": plant_info}, tech_config=config)
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

    # Check limiting factors
    # N2 limiting: index 0, H2 limiting: index 1, Electricity limiting: index 2
    # Capacity limiting: index 3
    assert pytest.approx(prob.get_val("synloop.limiting_input")[0]) == 0
    assert pytest.approx(prob.get_val("synloop.limiting_input")[1]) == 1
    assert pytest.approx(prob.get_val("synloop.limiting_input")[2]) == 2
    assert pytest.approx(prob.get_val("synloop.limiting_input")[3]) == 3
