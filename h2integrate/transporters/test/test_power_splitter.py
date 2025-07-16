import numpy as np
import pytest
import openmdao.api as om
from pytest import approx

from h2integrate.transporters.power_splitter import SplitterPerformanceModel


rng = np.random.default_rng(seed=0)


def test_splitter_ratio_mode():
    """Test the splitter in ratio mode with various split ratios."""
    prob = om.Problem()

    # Create tech config with ratio mode configuration
    tech_config = {
        "performance_model": {
            "config": {"split_mode": "ratio", "split_ratio": 0.3, "prescribed_electricity": 0.0}
        }
    }

    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=np.zeros(8760), units="kW")
    ivc.add_output("split_ratio", val=0.3)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    # Test with random electricity input
    electricity_input = rng.random(8760) * 1000  # Random values 0-1000 kW
    split_ratio = 0.3

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("split_ratio", split_ratio)
    prob.run_model()

    expected_output1 = electricity_input * split_ratio
    expected_output2 = electricity_input * (1.0 - split_ratio)

    assert prob.get_val("electricity_out1", units="kW") == approx(expected_output1, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(expected_output2, rel=1e-5)

    # Verify conservation of energy
    total_output = prob.get_val("electricity_out1", units="kW") + prob.get_val(
        "electricity_out2", units="kW"
    )
    assert total_output == approx(electricity_input, rel=1e-5)


def test_splitter_ratio_mode_edge_cases():
    """Test the splitter in ratio mode with edge case ratios."""
    tech_config = {
        "performance_model": {
            "config": {"split_mode": "ratio", "split_ratio": 0.0, "prescribed_electricity": 0.0}
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("split_ratio", val=0.0)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = 100.0

    # Test ratio = 0.0 (all power to output2)
    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("split_ratio", 0.0)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(electricity_input, rel=1e-5)

    # Test ratio = 1.0 (all power to output1)
    prob.set_val("split_ratio", 1.0)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(electricity_input, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(0.0, abs=1e-10)

    # Test ratio > 1.0 (should be clipped to 1.0)
    prob.set_val("split_ratio", 1.5)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(electricity_input, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(0.0, abs=1e-10)

    # Test ratio < 0.0 (should be clipped to 0.0)
    prob.set_val("split_ratio", -0.5)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(electricity_input, rel=1e-5)


def test_splitter_prescribed_electricity_mode():
    """Test the splitter in prescribed electricity mode."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "split_ratio": 0.5,
                "prescribed_electricity": 200.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=np.zeros(8760), units="kW")
    ivc.add_output("prescribed_electricity", val=np.zeros(8760), units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    # Test with electricity input that's always greater than prescribed electricity
    electricity_input = rng.random(8760) * 500 + 300  # Random values 300-800 kW
    prescribed_electricity = np.full(8760, 200.0)  # Prescribed 200 kW to output1

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("prescribed_electricity", prescribed_electricity, units="kW")
    prob.run_model()

    expected_output1 = prescribed_electricity
    expected_output2 = electricity_input - prescribed_electricity

    assert prob.get_val("electricity_out1", units="kW") == approx(expected_output1, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(expected_output2, rel=1e-5)

    # Verify conservation of energy
    total_output = prob.get_val("electricity_out1", units="kW") + prob.get_val(
        "electricity_out2", units="kW"
    )
    assert total_output == approx(electricity_input, rel=1e-5)


def test_splitter_prescribed_electricity_mode_limited_input():
    """Test the splitter in prescribed electricity mode when input is less than
    prescribed electricity."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "split_ratio": 0.5,
                "prescribed_electricity": 150.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=np.zeros(8760), units="kW")
    ivc.add_output("prescribed_electricity", val=np.zeros(8760), units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    # Test case where prescribed electricity exceeds available power
    electricity_input = np.full(8760, 100.0)  # 100 kW available
    prescribed_electricity = np.full(8760, 150.0)  # Want to send 150 kW to output1

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("prescribed_electricity", prescribed_electricity, units="kW")
    prob.run_model()

    # Should only send what's available (100 kW) to output1, nothing to output2
    expected_output1 = electricity_input  # Limited by available power
    expected_output2 = np.zeros(8760)

    assert prob.get_val("electricity_out1", units="kW") == approx(expected_output1, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(expected_output2, abs=1e-10)


def test_splitter_prescribed_electricity_mode_zero_input():
    """Test the splitter in prescribed electricity mode with zero input."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "split_ratio": 0.5,
                "prescribed_electricity": 50.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=0.0, units="kW")
    ivc.add_output("prescribed_electricity", val=50.0, units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    prob.set_val("electricity_in", 0.0, units="kW")
    prob.set_val("prescribed_electricity", 50.0, units="kW")
    prob.run_model()

    # With zero input, both outputs should be zero
    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(0.0, abs=1e-10)


def test_splitter_prescribed_electricity_mode_negative_prescribed_electricity():
    """Test the splitter in prescribed electricity mode with negative prescribed electricity."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "split_ratio": 0.5,
                "prescribed_electricity": -50.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("prescribed_electricity", val=-50.0, units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = 100.0
    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("prescribed_electricity", -50.0, units="kW")
    prob.run_model()

    # Negative prescribed electricity should be treated as zero
    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(electricity_input, rel=1e-5)


def test_splitter_invalid_mode():
    """Test that an invalid split mode raises an error."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "invalid_mode",
                "split_ratio": 0.5,
                "prescribed_electricity": 0.0,
            }
        }
    }

    with pytest.raises(
        ValueError,
        match="Invalid split_mode: invalid_mode. Must be 'ratio' or 'prescribed_electricity'",
    ):
        prob = om.Problem()
        comp = SplitterPerformanceModel(tech_config=tech_config)
        prob.model.add_subsystem("comp", comp, promotes=["*"])
        prob.setup()


def test_splitter_scalar_inputs():
    """Test the splitter with scalar inputs instead of arrays."""
    # Test ratio mode with scalars
    tech_config_ratio = {
        "performance_model": {
            "config": {"split_mode": "ratio", "split_ratio": 0.4, "prescribed_electricity": 0.0}
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config_ratio)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("split_ratio", val=0.4)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(40.0, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(60.0, rel=1e-5)

    # Test prescribed electricity mode with scalars
    tech_config_prescribed = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "split_ratio": 0.5,
                "prescribed_electricity": 30.0,
            }
        }
    }

    prob2 = om.Problem()
    comp2 = SplitterPerformanceModel(tech_config=tech_config_prescribed)
    prob2.model.add_subsystem("comp", comp2, promotes=["*"])
    ivc2 = om.IndepVarComp()
    ivc2.add_output("electricity_in", val=100.0, units="kW")
    ivc2.add_output("prescribed_electricity", val=30.0, units="kW")
    prob2.model.add_subsystem("ivc", ivc2, promotes=["*"])

    prob2.setup()
    prob2.run_model()

    assert prob2.get_val("electricity_out1", units="kW") == approx(30.0, rel=1e-5)
    assert prob2.get_val("electricity_out2", units="kW") == approx(70.0, rel=1e-5)


def test_splitter_with_explicit_config():
    """Test the splitter with explicit configuration."""
    # Test with complete tech config
    tech_config = {
        "performance_model": {
            "config": {"split_mode": "ratio", "split_ratio": 0.5, "prescribed_electricity": 0.0}
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("split_ratio", val=0.5)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()
    prob.run_model()

    # Should use ratio mode with 0.5 split ratio
    assert prob.get_val("electricity_out1", units="kW") == approx(50.0, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(50.0, rel=1e-5)


def test_splitter_config_object():
    """Test that the config object is created correctly."""
    from h2integrate.transporters.power_splitter import SplitterPerformanceConfig

    # Test config from dict with all required fields
    config_dict = {
        "split_mode": "prescribed_electricity",
        "prescribed_electricity": 100.0,
        "split_ratio": 0.7,
    }
    config = SplitterPerformanceConfig.from_dict(config_dict)
    assert config.split_mode == "prescribed_electricity"
    assert config.prescribed_electricity == 100.0
    assert config.split_ratio == 0.7

    # Test config with ratio mode
    config_dict_ratio = {"split_mode": "ratio", "split_ratio": 0.3, "prescribed_electricity": 0.0}
    config = SplitterPerformanceConfig.from_dict(config_dict_ratio)
    assert config.split_mode == "ratio"
    assert config.split_ratio == 0.3
    assert config.prescribed_electricity == 0.0


def test_splitter_missing_config():
    """Test that missing required config fields cause an error."""
    import pytest

    from h2integrate.transporters.power_splitter import SplitterPerformanceConfig

    # Test with missing fields should raise an error when trying to create config
    incomplete_config_dict = {
        "split_mode": "ratio"
        # Missing split_ratio and prescribed_electricity
    }

    with pytest.raises(AttributeError, match="missing the following inputs"):
        SplitterPerformanceConfig.from_dict(incomplete_config_dict)


def test_splitter_prescribed_electricity_default_value():
    """Test that the prescribed electricity input gets the default value from config."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "split_ratio": 0.5,
                "prescribed_electricity": 75.0,  # This should be the default input value
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    # Add prescribed_electricity output to test that default value from config is
    # used when not overridden
    ivc.add_output("prescribed_electricity", val=75.0, units="kW")  # Uses config default
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()
    prob.run_model()

    # Should use the provided value of 75.0 kW for prescribed_electricity
    assert prob.get_val("electricity_out1", units="kW") == approx(75.0, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(25.0, rel=1e-5)
