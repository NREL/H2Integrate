import os
import shutil
from pathlib import Path

import yaml
import pytest

from h2integrate.core.h2integrate_model import H2IntegrateModel
from h2integrate.core.inputs.validation import load_tech_yaml


examples_dir = Path(__file__).resolve().parent.parent.parent.parent / "examples/."


def test_custom_model_name_clash(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "01_onshore_steel_mn")

    # Path to the original tech_config.yaml and high-level yaml in the example directory
    orig_tech_config = Path.cwd() / "tech_config.yaml"
    temp_tech_config = Path.cwd() / "temp_tech_config.yaml"
    orig_highlevel_yaml = Path.cwd() / "01_onshore_steel_mn.yaml"
    temp_highlevel_yaml = Path.cwd() / "temp_01_onshore_steel_mn.yaml"

    # Copy the original tech_config.yaml and high-level yaml to temp files
    shutil.copy(orig_tech_config, temp_tech_config)
    shutil.copy(orig_highlevel_yaml, temp_highlevel_yaml)

    # Load the tech_config YAML content
    tech_config_data = load_tech_yaml(temp_tech_config)

    tech_config_data["technologies"]["electrolyzer"]["cost_model"] = {
        "model": "basic_electrolyzer_cost",
        "model_location": "dummy_path",  # path doesn't matter; just that `model_location` exists
    }

    # Save the modified tech_config YAML back
    with temp_tech_config.open("w") as f:
        yaml.safe_dump(tech_config_data, f)

    # Load the high-level YAML content
    with temp_highlevel_yaml.open() as f:
        highlevel_data = yaml.safe_load(f)

    # Modify the high-level YAML to point to the temp tech_config file
    highlevel_data["technology_config"] = str(temp_tech_config.name)

    # Save the modified high-level YAML back
    with temp_highlevel_yaml.open("w") as f:
        yaml.safe_dump(highlevel_data, f)

    # Assert that a ValueError is raised with the expected message when running the model
    error_msg = (
        r"Custom model_class_name or model_location specified for 'basic_electrolyzer_cost', "
        r"but 'basic_electrolyzer_cost' is a built-in H2Integrate model\. "
        r"Using built-in model instead is not allowed\. "
        r"If you want to use a custom model, please rename it in your configuration\."
    )
    with pytest.raises(ValueError, match=error_msg):
        H2IntegrateModel(temp_highlevel_yaml)

    # Clean up temporary YAML files
    temp_tech_config.unlink(missing_ok=True)
    temp_highlevel_yaml.unlink(missing_ok=True)


def test_custom_financial_model_grouping(subtests):
    # Change the current working directory to the example's directory
    os.chdir(examples_dir / "01_onshore_steel_mn")

    # Path to the original tech_config.yaml and high-level yaml in the example directory
    orig_tech_config = Path.cwd() / "tech_config.yaml"
    temp_tech_config = Path.cwd() / "temp_tech_config.yaml"
    orig_highlevel_yaml = Path.cwd() / "01_onshore_steel_mn.yaml"
    temp_highlevel_yaml = Path.cwd() / "temp_01_onshore_steel_mn.yaml"

    # Copy the original tech_config.yaml and high-level yaml to temp files
    shutil.copy(orig_tech_config, temp_tech_config)
    shutil.copy(orig_highlevel_yaml, temp_highlevel_yaml)

    # Load the tech_config YAML content
    tech_config_data = load_tech_yaml(temp_tech_config)

    # Modify the financial_model entry for one of the technologies
    tech_config_data["technologies"]["steel"]["financial_model"]["group"] = "test_financial_group"
    tech_config_data["technologies"]["electrolyzer"].pop("financial_model", None)

    # Save the modified tech_config YAML back
    with temp_tech_config.open("w") as f:
        yaml.safe_dump(tech_config_data, f)

    # Load the high-level YAML content
    with temp_highlevel_yaml.open() as f:
        highlevel_data = yaml.safe_load(f)

    # Modify the high-level YAML to point to the temp tech_config file
    highlevel_data["technology_config"] = str(temp_tech_config.name)

    # Save the modified high-level YAML back
    with temp_highlevel_yaml.open("w") as f:
        yaml.safe_dump(highlevel_data, f)

    # Run the model and check that it does not raise an error
    # (assuming custom financial_model is allowed)
    H2IntegrateModel(temp_highlevel_yaml)

    # Clean up temporary YAML files
    temp_tech_config.unlink(missing_ok=True)
    temp_highlevel_yaml.unlink(missing_ok=True)
