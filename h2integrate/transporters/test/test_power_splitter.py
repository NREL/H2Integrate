import numpy as np
import pytest
import openmdao.api as om
from pytest import approx

from h2integrate.transporters.power_splitter import (
    SplitterPerformanceModel,
    SplitterPerformanceConfig,
)


rng = np.random.default_rng(seed=0)


def test_splitter_ratio_mode():
    """Test the splitter in fraction mode with various split fractions."""
    prob = om.Problem()

    tech_config = {
        "performance_model": {
            "config": {"split_mode": "fraction", "fraction_of_electricity_to_first_tech": 0.3}
        }
    }

    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=np.zeros(8760), units="kW")
    ivc.add_output("fraction_of_electricity_to_first_tech", val=0.3)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = rng.random(8760) * 1000
    fraction_to_first = 0.3

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("fraction_of_electricity_to_first_tech", fraction_to_first)
    prob.run_model()

    expected_output1 = electricity_input * fraction_to_first
    expected_output2 = electricity_input * (1.0 - fraction_to_first)

    assert prob.get_val("electricity_out1", units="kW") == approx(expected_output1, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(expected_output2, rel=1e-5)

    total_output = prob.get_val("electricity_out1", units="kW") + prob.get_val(
        "electricity_out2", units="kW"
    )
    assert total_output == approx(electricity_input, rel=1e-5)


def test_splitter_ratio_mode_edge_cases():
    """Test the splitter in fraction mode with edge case fractions."""
    tech_config = {
        "performance_model": {
            "config": {"split_mode": "fraction", "fraction_of_electricity_to_first_tech": 0.0}
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("fraction_of_electricity_to_first_tech", val=0.0)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = 100.0

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("fraction_of_electricity_to_first_tech", 0.0)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(electricity_input, rel=1e-5)

    prob.set_val("fraction_of_electricity_to_first_tech", 1.0)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(electricity_input, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(0.0, abs=1e-10)

    prob.set_val("fraction_of_electricity_to_first_tech", 1.5)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(electricity_input, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(0.0, abs=1e-10)

    prob.set_val("fraction_of_electricity_to_first_tech", -0.5)
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(electricity_input, rel=1e-5)


def test_splitter_prescribed_electricity_mode():
    """Test the splitter in prescribed_electricity mode."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "prescribed_electricity_to_first_tech": 200.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=np.zeros(8760), units="kW")
    ivc.add_output("prescribed_electricity_to_first_tech", val=np.zeros(8760), units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = rng.random(8760) * 500 + 300
    prescribed_electricity = np.full(8760, 200.0)

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("prescribed_electricity_to_first_tech", prescribed_electricity, units="kW")
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
                "prescribed_electricity_to_first_tech": 150.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=np.zeros(8760), units="kW")
    ivc.add_output("prescribed_electricity_to_first_tech", val=np.zeros(8760), units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = np.full(8760, 100.0)
    prescribed_electricity = np.full(8760, 150.0)

    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("prescribed_electricity_to_first_tech", prescribed_electricity, units="kW")
    prob.run_model()

    expected_output1 = electricity_input
    expected_output2 = np.zeros(8760)

    assert prob.get_val("electricity_out1", units="kW") == approx(expected_output1, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(expected_output2, abs=1e-10)


def test_splitter_prescribed_electricity_mode_zero_input():
    """Test the splitter in prescribed_electricity mode with zero input."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "prescribed_electricity_to_first_tech": 50.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=0.0, units="kW")
    ivc.add_output("prescribed_electricity_to_first_tech", val=50.0, units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    prob.set_val("electricity_in", 0.0, units="kW")
    prob.set_val("prescribed_electricity_to_first_tech", 50.0, units="kW")
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(0.0, abs=1e-10)


def test_splitter_prescribed_electricity_mode_negative_prescribed_electricity():
    """Test the splitter in prescribed_electricity mode with negative prescribed electricity."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "prescribed_electricity_to_first_tech": -50.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("prescribed_electricity_to_first_tech", val=-50.0, units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input = 100.0
    prob.set_val("electricity_in", electricity_input, units="kW")
    prob.set_val("prescribed_electricity_to_first_tech", -50.0, units="kW")
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(0.0, abs=1e-10)
    assert prob.get_val("electricity_out2", units="kW") == approx(electricity_input, rel=1e-5)


def test_splitter_invalid_mode():
    """Test that an invalid split mode raises an error."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "invalid_mode",
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
            "config": {"split_mode": "fraction", "fraction_of_electricity_to_first_tech": 0.4}
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config_ratio)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("fraction_of_electricity_to_first_tech", val=0.4)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(40.0, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(60.0, rel=1e-5)

    tech_config_prescribed = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "prescribed_electricity_to_first_tech": 30.0,
            }
        }
    }

    prob2 = om.Problem()
    comp2 = SplitterPerformanceModel(tech_config=tech_config_prescribed)
    prob2.model.add_subsystem("comp", comp2, promotes=["*"])
    ivc2 = om.IndepVarComp()
    ivc2.add_output("electricity_in", val=100.0, units="kW")
    ivc2.add_output("prescribed_electricity_to_first_tech", val=30.0, units="kW")
    prob2.model.add_subsystem("ivc", ivc2, promotes=["*"])

    prob2.setup()
    prob2.run_model()

    assert prob2.get_val("electricity_out1", units="kW") == approx(30.0, rel=1e-5)
    assert prob2.get_val("electricity_out2", units="kW") == approx(70.0, rel=1e-5)


def test_splitter_with_explicit_config():
    """Test the splitter with explicit configuration."""
    tech_config = {
        "performance_model": {
            "config": {"split_mode": "fraction", "fraction_of_electricity_to_first_tech": 0.5}
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("fraction_of_electricity_to_first_tech", val=0.5)
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(50.0, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(50.0, rel=1e-5)


def test_splitter_config_object():
    """Test that the config object is created correctly."""

    config_dict = {
        "split_mode": "prescribed_electricity",
        "prescribed_electricity_to_first_tech": 100.0,
    }
    config = SplitterPerformanceConfig.from_dict(config_dict)
    assert config.split_mode == "prescribed_electricity"
    assert config.prescribed_electricity_to_first_tech == 100.0

    config_dict_ratio = {"split_mode": "fraction", "fraction_of_electricity_to_first_tech": 0.3}
    config = SplitterPerformanceConfig.from_dict(config_dict_ratio)
    assert config.split_mode == "fraction"
    assert config.fraction_of_electricity_to_first_tech == 0.3


def test_splitter_missing_config():
    """Test that missing required config fields cause an error."""

    incomplete_config_dict = {"split_mode": "fraction"}

    with pytest.raises(
        ValueError,
        match="fraction_of_electricity_to_first_tech is required when split_mode is 'fraction'",
    ):
        SplitterPerformanceConfig.from_dict(incomplete_config_dict)


def test_splitter_prescribed_electricity_default_value():
    """Test that the prescribed electricity input gets the default value from config."""
    tech_config = {
        "performance_model": {
            "config": {
                "split_mode": "prescribed_electricity",
                "prescribed_electricity_to_first_tech": 75.0,
            }
        }
    }

    prob = om.Problem()
    comp = SplitterPerformanceModel(tech_config=tech_config)
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in", val=100.0, units="kW")
    ivc.add_output("prescribed_electricity_to_first_tech", val=75.0, units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()
    prob.run_model()

    assert prob.get_val("electricity_out1", units="kW") == approx(75.0, rel=1e-5)
    assert prob.get_val("electricity_out2", units="kW") == approx(25.0, rel=1e-5)
