import numpy as np
import pytest
import openmdao.api as om
from pytest import fixture

from h2integrate.converters.natural_gas.natural_gas_cc_ct import (
    NaturalGasCostModel,
    NaturalGasPerformanceModel,
)


@fixture
def ngcc_performance_params():
    """Natural Gas Combined Cycle performance parameters."""
    tech_params = {
        "heat_rate": 7.5,  # MMBtu/MWh - typical for NGCC
    }
    return tech_params


@fixture
def ngct_performance_params():
    """Natural Gas Combustion Turbine performance parameters."""
    tech_params = {
        "heat_rate": 11.5,  # MMBtu/MWh - typical for NGCT
    }
    return tech_params


@fixture
def ngcc_cost_params():
    """Natural Gas Combined Cycle cost parameters."""
    cost_params = {
        "capex": 1000,  # $/kW
        "fopex": 10.0,  # $/kW/year
        "vopex": 2.5,  # $/MWh
        "heat_rate": 7.5,  # MMBtu/MWh
        "ng_price": 4.0,  # $/thousand cubic feet
        "project_life": 30,  # years
        "cost_year": 2023,
    }
    return cost_params


@fixture
def ngct_cost_params():
    """Natural Gas Combustion Turbine cost parameters."""
    cost_params = {
        "capex": 800,  # $/kW
        "fopex": 8.0,  # $/kW/year
        "vopex": 3.0,  # $/MWh
        "heat_rate": 11.5,  # MMBtu/MWh
        "ng_price": 4.0,  # $/thousand cubic feet
        "project_life": 30,  # years
        "cost_year": 2023,
    }
    return cost_params


def test_ngcc_performance(ngcc_performance_params, subtests):
    """Test NGCC performance model with typical operating conditions."""
    tech_config_dict = {
        "model_inputs": {
            "performance_parameters": ngcc_performance_params,
        }
    }

    # Create a simple natural gas input profile (constant 750 MMBtu/h for 100 MW plant)
    natural_gas_input = np.full(8760, 750.0)  # MMBtu

    prob = om.Problem()
    perf_comp = NaturalGasPerformanceModel(
        plant_config={},
        tech_config=tech_config_dict,
    )

    prob.model.add_subsystem("ng_perf", perf_comp, promotes=["*"])
    prob.setup()

    # Set the natural gas input
    prob.set_val("natural_gas_in", natural_gas_input)
    prob.run_model()

    electricity_out = prob.get_val("electricity_out")

    with subtests.test("NGCC Electricity Output"):
        # Expected: 750 MMBtu / 7.5 MMBtu/MWh = 100 MW
        expected_output = natural_gas_input / ngcc_performance_params["heat_rate"]
        assert pytest.approx(electricity_out, rel=1e-6) == expected_output

    with subtests.test("NGCC Average Output"):
        # Check average output is 100 MW
        assert pytest.approx(np.mean(electricity_out), rel=1e-6) == 100.0


def test_ngct_performance(ngct_performance_params, subtests):
    """Test NGCT performance model with typical operating conditions."""
    tech_config_dict = {
        "model_inputs": {
            "performance_parameters": ngct_performance_params,
        }
    }

    # Create a simple natural gas input profile (constant 575 MMBtu/h for 50 MW plant)
    natural_gas_input = np.full(8760, 575.0)  # MMBtu

    prob = om.Problem()
    perf_comp = NaturalGasPerformanceModel(
        plant_config={},
        tech_config=tech_config_dict,
    )

    prob.model.add_subsystem("ng_perf", perf_comp, promotes=["*"])
    prob.setup()

    # Set the natural gas input
    prob.set_val("natural_gas_in", natural_gas_input)
    prob.run_model()

    electricity_out = prob.get_val("electricity_out")

    with subtests.test("NGCT Electricity Output"):
        # Expected: 575 MMBtu / 11.5 MMBtu/MWh = 50 MW
        expected_output = natural_gas_input / ngct_performance_params["heat_rate"]
        assert pytest.approx(electricity_out, rel=1e-6) == expected_output

    with subtests.test("NGCT Average Output"):
        # Check average output is 50 MW
        assert pytest.approx(np.mean(electricity_out), rel=1e-6) == 50.0


def test_ngcc_cost(ngcc_cost_params, subtests):
    """Test NGCC cost model calculations."""
    tech_config_dict = {
        "model_inputs": {
            "cost_parameters": ngcc_cost_params,
        }
    }

    # Plant parameters for a 100 MW NGCC plant
    plant_capacity_kW = 100_000  # 100 MW
    annual_generation_MWh = 700_000  # ~80% capacity factor

    prob = om.Problem()
    cost_comp = NaturalGasCostModel(
        plant_config={},
        tech_config=tech_config_dict,
    )

    prob.model.add_subsystem("ng_cost", cost_comp, promotes=["*"])
    prob.setup()

    # Set inputs
    prob.set_val("plant_capacity_kW", plant_capacity_kW)
    prob.set_val("delivered_electricity_MWh", annual_generation_MWh)
    prob.run_model()

    capex = prob.get_val("CapEx")[0]
    opex = prob.get_val("OpEx")[0]
    cost_year = prob.get_val("cost_year")

    # Calculate expected values
    expected_capex = ngcc_cost_params["capex"] * plant_capacity_kW
    expected_fixed_om = (
        ngcc_cost_params["fopex"] * plant_capacity_kW * ngcc_cost_params["project_life"]
    )
    expected_variable_om = (
        ngcc_cost_params["vopex"] * annual_generation_MWh * ngcc_cost_params["project_life"]
    )
    expected_fuel_cost = (
        ngcc_cost_params["ng_price"]
        * ngcc_cost_params["heat_rate"]
        * annual_generation_MWh
        * ngcc_cost_params["project_life"]
        / 1.036
    )
    expected_opex = expected_fixed_om + expected_variable_om + expected_fuel_cost

    with subtests.test("NGCC Capital Cost"):
        assert pytest.approx(capex, rel=1e-6) == expected_capex

    with subtests.test("NGCC Operating Cost"):
        assert pytest.approx(opex, rel=1e-6) == expected_opex

    with subtests.test("NGCC Cost Year"):
        assert cost_year == ngcc_cost_params["cost_year"]


def test_ngct_cost(ngct_cost_params, subtests):
    """Test NGCT cost model calculations."""
    tech_config_dict = {
        "model_inputs": {
            "cost_parameters": ngct_cost_params,
        }
    }

    # Plant parameters for a 50 MW NGCT plant
    plant_capacity_kW = 50_000  # 50 MW
    annual_generation_MWh = 100_000  # ~23% capacity factor (peaking plant)

    prob = om.Problem()
    cost_comp = NaturalGasCostModel(
        plant_config={},
        tech_config=tech_config_dict,
    )

    prob.model.add_subsystem("ng_cost", cost_comp, promotes=["*"])
    prob.setup()

    # Set inputs
    prob.set_val("plant_capacity_kW", plant_capacity_kW)
    prob.set_val("delivered_electricity_MWh", annual_generation_MWh)
    prob.run_model()

    capex = prob.get_val("CapEx")[0]
    opex = prob.get_val("OpEx")[0]
    cost_year = prob.get_val("cost_year")

    # Calculate expected values
    expected_capex = ngct_cost_params["capex"] * plant_capacity_kW
    expected_fixed_om = (
        ngct_cost_params["fopex"] * plant_capacity_kW * ngct_cost_params["project_life"]
    )
    expected_variable_om = (
        ngct_cost_params["vopex"] * annual_generation_MWh * ngct_cost_params["project_life"]
    )
    expected_fuel_cost = (
        ngct_cost_params["ng_price"]
        * ngct_cost_params["heat_rate"]
        * annual_generation_MWh
        * ngct_cost_params["project_life"]
        / 1.036
    )
    expected_opex = expected_fixed_om + expected_variable_om + expected_fuel_cost

    with subtests.test("NGCT Capital Cost"):
        assert pytest.approx(capex, rel=1e-6) == expected_capex

    with subtests.test("NGCT Operating Cost"):
        assert pytest.approx(opex, rel=1e-6) == expected_opex

    with subtests.test("NGCT Cost Year"):
        assert cost_year == ngct_cost_params["cost_year"]


def test_variable_ng_price(ngcc_cost_params, subtests):
    """Test cost model with variable natural gas price."""
    # Modify cost parameters to use variable pricing
    cost_params = ngcc_cost_params.copy()
    cost_params["ng_price"] = "variable"

    tech_config_dict = {
        "model_inputs": {
            "cost_parameters": cost_params,
        }
    }

    plant_capacity_kW = 100_000
    annual_generation_MWh = 700_000

    prob = om.Problem()
    cost_comp = NaturalGasCostModel(
        plant_config={},
        tech_config=tech_config_dict,
    )

    prob.model.add_subsystem("ng_cost", cost_comp, promotes=["*"])
    prob.setup()

    prob.set_val("plant_capacity_kW", plant_capacity_kW)
    prob.set_val("delivered_electricity_MWh", annual_generation_MWh)
    prob.run_model()

    opex = prob.get_val("OpEx")[0]

    # Calculate expected OpEx without fuel costs
    expected_fixed_om = cost_params["fopex"] * plant_capacity_kW * cost_params["project_life"]
    expected_variable_om = (
        cost_params["vopex"] * annual_generation_MWh * cost_params["project_life"]
    )
    expected_opex = expected_fixed_om + expected_variable_om  # No fuel cost

    with subtests.test("Variable NG Price OpEx"):
        assert pytest.approx(opex, rel=1e-6) == expected_opex


def test_combined_performance_and_cost(ngcc_performance_params, ngcc_cost_params, subtests):
    """Test combined performance and cost model simulation."""
    tech_config_dict = {
        "model_inputs": {
            "performance_parameters": ngcc_performance_params,
            "cost_parameters": ngcc_cost_params,
        }
    }

    # Create natural gas input for 100 MW plant
    natural_gas_input = np.full(8760, 750.0)  # MMBtu/h

    prob = om.Problem()
    perf_comp = NaturalGasPerformanceModel(
        plant_config={},
        tech_config=tech_config_dict,
    )
    cost_comp = NaturalGasCostModel(
        plant_config={},
        tech_config=tech_config_dict,
    )

    prob.model.add_subsystem("ng_perf", perf_comp)
    prob.model.add_subsystem("ng_cost", cost_comp)

    # Don't connect directly due to units incompatibility
    # The cost model expects annual generation, not hourly time series

    prob.setup()

    # Set inputs
    prob.set_val("ng_perf.natural_gas_in", natural_gas_input)
    prob.set_val("ng_cost.plant_capacity_kW", 100_000)  # 100 MW capacity

    # Run performance model first
    prob.run_model()

    electricity_out = prob.get_val("ng_perf.electricity_out")
    annual_generation = np.sum(electricity_out)  # MWh

    # Now set the annual generation for the cost model and re-run
    prob.set_val("ng_cost.delivered_electricity_MWh", annual_generation)
    prob.run_model()

    capex = prob.get_val("ng_cost.CapEx")[0]
    prob.get_val("ng_cost.OpEx")[0]

    with subtests.test("Combined Model Electricity Output"):
        # Should generate 100 MW * 8760 hours = 876,000 MWh
        assert pytest.approx(annual_generation, rel=1e-6) == 876_000

    with subtests.test("Combined Model CapEx"):
        expected_capex = ngcc_cost_params["capex"] * 100_000
        assert pytest.approx(capex, rel=1e-6) == expected_capex
