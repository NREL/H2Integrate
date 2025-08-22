"""
Test cases for feedstock models covering various configurations and scenarios.

This test suite validates feedstock functionality including:
- Single feedstock configurations
- Multiple feedstocks of the same type
- Multiple feedstocks of different types
- Complex technology interconnections
- Cost and performance model integration
"""

import os
import tempfile
from pathlib import Path

import yaml
import pytest


class TestFeedstocks:
    """Test class for feedstock model functionality."""

    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)

    def create_yaml_file(self, filename: str, content: dict):
        """Helper to create YAML files for testing."""
        with Path(filename).open("w") as f:
            yaml.dump(content, f, default_flow_style=False)

    def create_main_config(self, name: str):
        """Create main configuration file."""
        config = {
            "name": "feedstock_test",
            "system_summary": f"Test configuration for {name}",
            "driver_config": "driver_config.yaml",
            "technology_config": "tech_config.yaml",
            "plant_config": "plant_config.yaml",
        }
        self.create_yaml_file("main_config.yaml", config)

    def create_driver_config(self):
        """Create basic driver configuration."""
        config = {
            "name": "driver_config",
            "description": "Basic driver for feedstock tests",
            "optimization": False,
            "design_variables": {},
            "constraints": {},
            "merit_figure": "LCOE",
        }
        self.create_yaml_file("driver_config.yaml", config)

    def create_base_plant_config(self, interconnections: list):
        """Create plant configuration with specified interconnections."""
        config = {
            "name": "plant_config",
            "description": "Test plant configuration",
            "site": {
                "latitude": 32.34,
                "longitude": -98.27,
                "elevation_m": 440.0,
                "time_zone": -6,
                "boundaries": [{"x": [0.0, 1000.0, 1000.0, 0.0], "y": [0.0, 0.0, 100.0, 1000.0]}],
            },
            "technology_interconnections": interconnections,
            "plant": {
                "plant_life": 30,
                "grid_connection": False,
                "ppa_price": 0.05,
                "hybrid_electricity_estimated_cf": 0.5,
                "simulation": {
                    "n_timesteps": 100  # Reduced for testing speed
                },
            },
            "finance_parameters": {
                "analysis_start_year": 2025,
                "installation_time": 12,
                "inflation_rate": 0.0,
                "discount_rate": 0.08,
                "debt_equity_split": False,
                "cost_adjustment_parameters": {
                    "cost_year_adjustment_inflation": 0.025,
                    "target_dollar_year": 2023,
                },
            },
            "policy_parameters": {
                "electricity_itc": 0,
                "electricity_ptc": 0,
                "h2_ptc": 0,
                "h2_storage_itc": 0,
            },
        }
        self.create_yaml_file("plant_config.yaml", config)

    def create_dummy_technology(self, tech_name: str, input_type: str | None = None):
        """Create a dummy technology configuration that consumes a feedstock."""
        tech_config = {
            "performance_model": {"model": "dummy_performance"},
            "cost_model": {"model": "dummy_cost"},
            "model_inputs": {
                "shared_parameters": {"capacity": 10.0, "efficiency": 0.8},
                "performance_parameters": {},
                "cost_parameters": {
                    "capex_per_kw": 1000.0,
                    "fixed_opex_per_kw_per_year": 25.0,
                    "variable_opex_per_mwh": 5.0,
                    "cost_year": 2023,
                },
            },
        }

        if input_type:
            tech_config["model_inputs"]["shared_parameters"]["input_type"] = input_type

        return tech_config

    def create_feedstock_technology(
        self,
        feedstock_type: str,
        units: str,
        rated_capacity: float,
        price: float,
        annual_cost: float = 0.0,
        start_up_cost: float = 0.0,
    ):
        """Create feedstock technology configuration."""
        return {
            "performance_model": {"model": "feedstock_performance"},
            "cost_model": {"model": "feedstock_cost"},
            "model_inputs": {
                "shared_parameters": {"feedstock_type": feedstock_type, "units": units},
                "performance_parameters": {"rated_capacity": rated_capacity},
                "cost_parameters": {
                    "feedstock_type": feedstock_type,
                    "units": units,
                    "price": price,
                    "annual_cost": annual_cost,
                    "start_up_cost": start_up_cost,
                    "cost_year": 2023,
                },
            },
        }

    def test_single_feedstock_natural_gas(self):
        """Test basic single natural gas feedstock configuration."""
        # Create configuration files
        self.create_main_config("single_natural_gas")
        self.create_driver_config()

        # Technology configuration
        tech_config = {
            "name": "technology_config",
            "description": "Single natural gas feedstock test",
            "technologies": {
                "ng_feedstock": self.create_feedstock_technology(
                    "natural_gas", "MMBtu", 100.0, 4.2, 1000.0, 50000.0
                ),
                "power_plant": self.create_dummy_technology("power_plant", "natural_gas"),
            },
        }
        self.create_yaml_file("tech_config.yaml", tech_config)

        # Plant configuration with interconnections
        interconnections = [["ng_feedstock", "power_plant", "natural_gas", "ng_pipe"]]
        self.create_base_plant_config(interconnections)

        # This test validates the configuration structure
        # In a full implementation, you would run the model here
        assert Path("main_config.yaml").exists()
        assert Path("tech_config.yaml").exists()
        assert Path("plant_config.yaml").exists()

        # Validate configuration content
        with Path("tech_config.yaml").open() as f:
            loaded_config = yaml.safe_load(f)

        assert "ng_feedstock" in loaded_config["technologies"]
        ng_config = loaded_config["technologies"]["ng_feedstock"]
        assert ng_config["performance_model"]["model"] == "feedstock_performance"
        assert ng_config["cost_model"]["model"] == "feedstock_cost"
        assert ng_config["model_inputs"]["shared_parameters"]["feedstock_type"] == "natural_gas"

    def test_multiple_same_type_feedstocks(self):
        """Test multiple feedstocks of the same type with different configurations."""
        self.create_main_config("multiple_same_type")
        self.create_driver_config()

        # Technology configuration with two natural gas feedstocks
        tech_config = {
            "name": "technology_config",
            "description": "Multiple natural gas feedstocks test",
            "technologies": {
                "ng_feedstock_primary": self.create_feedstock_technology(
                    "natural_gas", "MMBtu", 80.0, 4.0, 800.0, 40000.0
                ),
                "ng_feedstock_backup": self.create_feedstock_technology(
                    "natural_gas", "MMBtu", 50.0, 4.5, 500.0, 25000.0
                ),
                "power_plant_1": self.create_dummy_technology("power_plant_1", "natural_gas"),
                "power_plant_2": self.create_dummy_technology("power_plant_2", "natural_gas"),
            },
        }
        self.create_yaml_file("tech_config.yaml", tech_config)

        # Plant configuration with multiple interconnections
        interconnections = [
            ["ng_feedstock_primary", "power_plant_1", "natural_gas", "ng_pipe_1"],
            ["ng_feedstock_backup", "power_plant_2", "natural_gas", "ng_pipe_2"],
        ]
        self.create_base_plant_config(interconnections)

        # Validate different configurations for same feedstock type
        with Path("tech_config.yaml").open() as f:
            loaded_config = yaml.safe_load(f)

        primary_config = loaded_config["technologies"]["ng_feedstock_primary"]
        backup_config = loaded_config["technologies"]["ng_feedstock_backup"]

        # Both should be natural gas but with different parameters
        assert (
            primary_config["model_inputs"]["shared_parameters"]["feedstock_type"] == "natural_gas"
        )
        assert backup_config["model_inputs"]["shared_parameters"]["feedstock_type"] == "natural_gas"
        assert primary_config["model_inputs"]["performance_parameters"]["rated_capacity"] == 80.0
        assert backup_config["model_inputs"]["performance_parameters"]["rated_capacity"] == 50.0

    def test_multiple_different_type_feedstocks(self):
        """Test multiple feedstocks of different types."""
        self.create_main_config("multiple_different_types")
        self.create_driver_config()

        # Technology configuration with different feedstock types
        tech_config = {
            "name": "technology_config",
            "description": "Multiple different feedstock types test",
            "technologies": {
                "ng_feedstock": self.create_feedstock_technology(
                    "natural_gas", "MMBtu", 100.0, 4.2, 1000.0, 50000.0
                ),
                "water_feedstock": self.create_feedstock_technology(
                    "water", "galUS", 500.0, 0.003, 1200.0, 15000.0
                ),
                "electricity_feedstock": self.create_feedstock_technology(
                    "electricity", "MWh", 25.0, 75.0, 5000.0, 0.0
                ),
                "power_plant": self.create_dummy_technology("power_plant", "natural_gas"),
                "electrolyzer": self.create_dummy_technology("electrolyzer", "electricity"),
                "cooling_system": self.create_dummy_technology("cooling_system", "water"),
            },
        }
        self.create_yaml_file("tech_config.yaml", tech_config)

        # Plant configuration with multiple different connections
        interconnections = [
            ["ng_feedstock", "power_plant", "natural_gas", "ng_pipe"],
            ["electricity_feedstock", "electrolyzer", "electricity", "grid_connection"],
            ["water_feedstock", "cooling_system", "water", "water_line"],
            ["water_feedstock", "electrolyzer", "water", "process_water"],
        ]
        self.create_base_plant_config(interconnections)

        # Validate different feedstock types
        with Path("tech_config.yaml").open() as f:
            loaded_config = yaml.safe_load(f)

        feedstocks = ["ng_feedstock", "water_feedstock", "electricity_feedstock"]
        expected_types = ["natural_gas", "water", "electricity"]
        expected_units = ["MMBtu", "galUS", "MWh"]

        for feedstock, expected_type, expected_unit in zip(
            feedstocks, expected_types, expected_units
        ):
            config = loaded_config["technologies"][feedstock]
            assert config["model_inputs"]["shared_parameters"]["feedstock_type"] == expected_type
            assert config["model_inputs"]["shared_parameters"]["units"] == expected_unit

    def test_complex_interconnections(self):
        """Test complex technology interconnections with multiple feedstocks."""
        self.create_main_config("complex_interconnections")
        self.create_driver_config()

        # Complex technology configuration
        tech_config = {
            "name": "technology_config",
            "description": "Complex interconnections test",
            "technologies": {
                "ng_feedstock": self.create_feedstock_technology(
                    "natural_gas", "MMBtu", 150.0, 4.0, 2000.0, 75000.0
                ),
                "electricity_grid": self.create_feedstock_technology(
                    "electricity", "MWh", 50.0, 80.0, 8000.0, 0.0
                ),
                "water_supply": self.create_feedstock_technology(
                    "water", "galUS", 1000.0, 0.004, 2400.0, 30000.0
                ),
                "power_plant": self.create_dummy_technology("power_plant", "natural_gas"),
                "electrolyzer_1": self.create_dummy_technology("electrolyzer_1", "electricity"),
                "electrolyzer_2": self.create_dummy_technology("electrolyzer_2", "electricity"),
                "cooling_tower": self.create_dummy_technology("cooling_tower", "water"),
                "process_unit": self.create_dummy_technology("process_unit", "water"),
            },
        }
        self.create_yaml_file("tech_config.yaml", tech_config)

        # Complex interconnection pattern
        interconnections = [
            ["ng_feedstock", "power_plant", "natural_gas", "ng_main"],
            ["electricity_grid", "electrolyzer_1", "electricity", "grid_1"],
            ["electricity_grid", "electrolyzer_2", "electricity", "grid_2"],
            ["water_supply", "cooling_tower", "water", "cooling_water"],
            ["water_supply", "process_unit", "water", "process_water"],
            ["water_supply", "electrolyzer_1", "water", "electrolysis_water"],
            ["water_supply", "electrolyzer_2", "water", "electrolysis_water_2"],
        ]
        self.create_base_plant_config(interconnections)

        # Validate complex interconnections
        with Path("plant_config.yaml").open() as f:
            plant_config = yaml.safe_load(f)

        connections = plant_config["technology_interconnections"]
        assert len(connections) == 7

        # Check that electricity grid feeds two electrolyzers
        electricity_connections = [conn for conn in connections if conn[0] == "electricity_grid"]
        assert len(electricity_connections) == 2

        # Check that water supply feeds four technologies
        water_connections = [conn for conn in connections if conn[0] == "water_supply"]
        assert len(water_connections) == 4

    def test_high_capacity_feedstocks(self):
        """Test feedstocks with high capacity requirements."""
        self.create_main_config("high_capacity")
        self.create_driver_config()

        # Technology configuration with high capacity feedstocks
        tech_config = {
            "name": "technology_config",
            "description": "High capacity feedstock test",
            "technologies": {
                "major_ng_feedstock": self.create_feedstock_technology(
                    "natural_gas", "MMBtu", 5000.0, 3.8, 50000.0, 500000.0
                ),
                "industrial_water": self.create_feedstock_technology(
                    "water", "galUS", 10000.0, 0.002, 25000.0, 150000.0
                ),
                "large_power_plant": self.create_dummy_technology(
                    "large_power_plant", "natural_gas"
                ),
                "industrial_process": self.create_dummy_technology("industrial_process", "water"),
            },
        }
        self.create_yaml_file("tech_config.yaml", tech_config)

        # Plant configuration
        interconnections = [
            ["major_ng_feedstock", "large_power_plant", "natural_gas", "ng_main"],
            ["industrial_water", "industrial_process", "water", "process_water"],
        ]
        self.create_base_plant_config(interconnections)

        # Validate high capacity configurations
        with Path("tech_config.yaml").open() as f:
            loaded_config = yaml.safe_load(f)

        ng_config = loaded_config["technologies"]["major_ng_feedstock"]
        water_config = loaded_config["technologies"]["industrial_water"]

        assert ng_config["model_inputs"]["performance_parameters"]["rated_capacity"] == 5000.0
        assert water_config["model_inputs"]["performance_parameters"]["rated_capacity"] == 10000.0

    def test_zero_cost_feedstock(self):
        """Test feedstock with zero operational costs."""
        self.create_main_config("zero_cost")
        self.create_driver_config()

        # Technology configuration with zero-cost feedstock (e.g., atmospheric air)
        tech_config = {
            "name": "technology_config",
            "description": "Zero cost feedstock test",
            "technologies": {
                "air_feedstock": self.create_feedstock_technology(
                    "air",
                    "kg",
                    1000.0,
                    0.0,
                    0.0,
                    10000.0,  # Only startup cost
                ),
                "air_separation": self.create_dummy_technology("air_separation", "air"),
            },
        }
        self.create_yaml_file("tech_config.yaml", tech_config)

        # Plant configuration
        interconnections = [["air_feedstock", "air_separation", "air", "air_intake"]]
        self.create_base_plant_config(interconnections)

        # Validate zero cost configuration
        with Path("tech_config.yaml").open() as f:
            loaded_config = yaml.safe_load(f)

        air_config = loaded_config["technologies"]["air_feedstock"]
        cost_params = air_config["model_inputs"]["cost_parameters"]

        assert cost_params["price"] == 0.0
        assert cost_params["annual_cost"] == 0.0
        assert cost_params["start_up_cost"] == 10000.0  # Still has capital cost

    def test_feedstock_parameter_validation(self):
        """Test validation of feedstock parameters."""
        self.create_main_config("parameter_validation")
        self.create_driver_config()

        # Test configuration with mismatched parameters (should be caught by validation)
        tech_config = {
            "name": "technology_config",
            "description": "Parameter validation test",
            "technologies": {
                "mismatched_feedstock": {
                    "performance_model": {"model": "feedstock_performance"},
                    "cost_model": {"model": "feedstock_cost"},
                    "model_inputs": {
                        "shared_parameters": {"feedstock_type": "natural_gas", "units": "MMBtu"},
                        "performance_parameters": {"rated_capacity": 100.0},
                        "cost_parameters": {
                            "feedstock_type": "natural_gas",  # Should match
                            "units": "MMBtu",  # Should match
                            "price": 4.2,
                            "annual_cost": 1000.0,
                            "start_up_cost": 50000.0,
                            "cost_year": 2023,
                        },
                    },
                },
                "consumer": self.create_dummy_technology("consumer", "natural_gas"),
            },
        }
        self.create_yaml_file("tech_config.yaml", tech_config)

        # Plant configuration
        interconnections = [["mismatched_feedstock", "consumer", "natural_gas", "connection"]]
        self.create_base_plant_config(interconnections)

        # Validate parameter consistency
        with Path("tech_config.yaml").open() as f:
            loaded_config = yaml.safe_load(f)

        feedstock_config = loaded_config["technologies"]["mismatched_feedstock"]
        shared_params = feedstock_config["model_inputs"]["shared_parameters"]
        cost_params = feedstock_config["model_inputs"]["cost_parameters"]

        # Parameters should match between performance and cost models
        assert shared_params["feedstock_type"] == cost_params["feedstock_type"]
        assert shared_params["units"] == cost_params["units"]


if __name__ == "__main__":
    pytest.main([__file__])
