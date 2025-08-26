import numpy as np
import pytest
import openmdao.api as om
from pytest import approx

from h2integrate.transporters.electricity_splitter import (
    SplitterPerformanceModel,
    SplitterPerformanceConfig,
)


rng = np.random.default_rng(seed=0)


def test_splitter_ratio_mode_edge_cases():
    """Test the splitter in fraction mode with edge case fractions."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "fraction",
                "priority_tech": "electrolyzer",
                "fraction_to_priority_tech": 0.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("fraction_to_priority_tech", val=0.0)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = 100.0

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("fraction_to_priority_tech", 0.0)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(electricity_input, rel=1e-5)

    prob.set_val("fraction_to_priority_tech", 1.0)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(electricity_input, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(0.0, abs=1e-10)

    prob.set_val("fraction_to_priority_tech", 1.5)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(electricity_input, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(0.0, abs=1e-10)

    prob.set_val("fraction_to_priority_tech", -0.5)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(electricity_input, rel=1e-5)


def test_splitter_prescribed_electricity_mode():
    """Test the splitter in prescribed_electricity mode."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "priority_tech": "electrolyzer",
                "prescribed_electricity_to_priority_tech": 200.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=np.zeros(8760), units="kW")
    ivc.add_output("prescribed_electricity_to_priority_tech", val=np.zeros(8760), units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = rng.random(8760) * 500 + 300
    prescribed_electricity = np.full(8760, 200.0)

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("prescribed_electricity_to_priority_tech", prescribed_electricity, units="kW")
    prob.run_model()

    expected_output1 = prescribed_electricity
    expected_output2 = electricity_input - prescribed_electricity

    assert prob.get_val("electricity_out1", units="kW") == approx(expected_output1, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(expected_output2, rel=1e-5)

    total_output = prob.get_val("electricity_out1", units="kW") + prob.get_val(
        "electricity_out2", units="kW"
    )
    assert total_output == approx(electricity_input, rel=1e-5)


def test_splitter_prescribed_electricity_mode_limited_input():
    """
    Test the splitter in prescribed_electricity mode
    when input is less than prescribed electricity.
    """
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "priority_tech": "electrolyzer",
                "prescribed_electricity_to_priority_tech": 150.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=np.zeros(8760), units="kW")
    ivc.add_output("prescribed_electricity_to_priority_tech", val=np.zeros(8760), units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = np.full(8760, 100.0)
    prescribed_electricity = np.full(8760, 150.0)

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("prescribed_electricity_to_priority_tech", prescribed_electricity, units="kW")
    prob.run_model()

    expected_output1 = electricity_input
    expected_output2 = np.zeros(8760)

    assert prob.get_val("electricity_out1", units="kW") == approx(expected_output1, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(expected_output2, abs=1e-10)


def test_splitter_invalid_mode():
    """Test that an invalid split mode raises an error."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "invalid_mode",
                "priority_tech": "electrolyzer",
            }
        }
    }

    with pytest.raises(
        ValueError,
        match="Invalid split_mode: invalid_mode. Must be 'fraction' or 'prescribed_electricity'",
    ):
        prob = om.Problem()
        comp = SplitterPerformanceModel(tech_config=tech_config)
        prob.model.add_subsystem("comp", comp, promotes=["*"])
        prob.setup()


def test_splitter_scalar_inputs():
    """Test the splitter with scalar inputs instead of arrays."""
    tech_config_ratio = {
        "performance_model": {
            "config": {
                "split_mode": "fraction",
                "priority_tech": "electrolyzer",
                "fraction_to_priority_tech": 0.4,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config_ratio)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("fraction_to_priority_tech", val=0.4)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(40.0, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(60.0, rel=1e-5)

    tech_config_prescribed = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "priority_tech": "electrolyzer",
                "prescribed_electricity_to_priority_tech": 30.0,
            }
        }
    }

    prob2 = om.Problem()
    comp2 = SplitterPerformanceModel(tech_config=tech_config_prescribed)
    prob2.model.add_subsystem("comp", comp2, promotes=["*"])
    ivc2 = om.IndepVarComp()
    ivc2.add_output("electricity_in", val=100.0, units="kW")
    ivc2.add_output("prescribed_electricity_to_priority_tech", val=30.0, units="kW")
    prob2.model.add_subsystem("ivc", ivc2, promotes=["*"])

    prob2.setup()
    prob2.run_model()

    assert prob2.get_val("electricity_out1", units="kW") == approx(30.0, rel=1e-5)
    assert prob2.get_val("electricity_out2", units="kW") == approx(70.0, rel=1e-5)


def test_splitter_prescribed_electricity_varied_array():
    """Test the splitter in prescribed_electricity mode with a varied array (50-100 MW)."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "priority_tech": "electrolyzer",
                "prescribed_electricity_to_priority_tech": 75000.0,  # Default value in kW
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=np.zeros(8760), units="kW")
    ivc.add_output("prescribed_electricity_to_priority_tech", val=np.zeros(8760), units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    # Generate varied prescribed electricity array between 50-100 MW (50,000-100,000 kW)
    prescribed_electricity = rng.random(8760) * 50000 + 50000  # 50-100 MW range

    # Input electricity should be higher than prescribed to test both scenarios
    electricity_input = rng.random(8760) * 30000 + 120000  # 120-150 MW range

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("prescribed_electricity_to_priority_tech", prescribed_electricity, units="kW")
    prob.run_model()

    # Since input > prescribed in all cases, prescribed should go to output1
    expected_output1 = prescribed_electricity
    expected_output2 = electricity_input - prescribed_electricity

    assert prob.get_val("electricity_out1", units="kW") == approx(expected_output1, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(expected_output2, rel=1e-5)

    # Verify total conservation of energy
    total_output = prob.get_val("electricity_out1", units="kW") + prob.get_val(
        "electricity_out2", units="kW"
    )
    assert total_output == approx(electricity_input, rel=1e-5)

    # Test with some time steps where prescribed > available
    electricity_input_limited = rng.random(8760) * 30000 + 20000  # 20-50 MW range
    prob.set_val("electricity_in", electricity_input_limited, units="kW")
    prob.run_model()

    expected_output1_limited = np.minimum(prescribed_electricity, electricity_input_limited)
    expected_output2_limited = electricity_input_limited - expected_output1_limited

    assert prob.get_val("electricity_out1", units="kW") == approx(
        expected_output1_limited, rel=1e-5
    )
    assert prob.get_val("electricity_out2", units="kW") == approx(
        expected_output2_limited, rel=1e-5
    )


def test_splitter_missing_config():
    """Test that missing required config fields cause an error."""

    incomplete_config_dict = {"split_mode": "fraction", "priority_tech": "electrolyzer"}

    with pytest.raises(
        ValueError,
        match="fraction_to_priority_tech is required when split_mode is 'fraction'",
    ):
        SplitterPerformanceConfig.from_dict(incomplete_config_dict)
