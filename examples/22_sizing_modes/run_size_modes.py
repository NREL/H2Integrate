from pathlib import Path

from h2integrate.core.h2integrate_model import H2IntegrateModel
from h2integrate.core.inputs.validation import load_tech_yaml


# load the tech config
tech_config = load_tech_yaml(Path(__file__).parent / "tech_config.yaml")

sizing_modes = ["normal", "iterative", "optimizer"]

# loop through the various sizing options
for mode in sizing_modes:
    plant_config_fname = (
        "plant_config_iterative.yaml" if mode == "iterative" else "plant_config.yaml"
    )
    driver_config_fname = (
        "driver_config_optimizer.yaml" if mode == "optimizer" else "driver_config.yaml"
    )
    if mode == "normal":
        # modify the tech config
        tech_config["technologies"]["electrolyzer"]["model_inputs"]["performance_parameters"][
            "sizing"
        ] = {
            "size_mode": "normal",
        }
        tech_config["technologies"]["ammonia"]["model_inputs"]["performance_parameters"][
            "sizing"
        ] = {
            "size_mode": "normal",
        }
    if mode == "iterative":
        # modify the tech config
        tech_config["technologies"]["electrolyzer"]["model_inputs"]["performance_parameters"][
            "sizing"
        ] = {
            "size_mode": "resize_by_max_commodity",
            "flow_used_for_sizing": "hydrogen",
            "max_hydrogen_ratio": 1.0,
        }
        tech_config["technologies"]["ammonia"]["model_inputs"]["performance_parameters"][
            "sizing"
        ] = {
            "size_mode": "normal",
        }

    if mode == "optimizer":
        # modify the tech config
        tech_config["technologies"]["electrolyzer"]["model_inputs"]["performance_parameters"][
            "sizing"
        ] = {
            "size_mode": "resize_by_max_feedstock",
            "flow_used_for_sizing": "electricity",
            "max_hydrogen_ratio": 1.0,
        }
        tech_config["technologies"]["ammonia"]["model_inputs"]["performance_parameters"][
            "sizing"
        ] = {
            "size_mode": "resize_by_max_feedstock",
            "flow_used_for_sizing": "hydrogen",
            "max_feedstock_ratio": 1.0,
        }

    # Create the H2I input config
    input_config = {
        "name": "H2Integrate_config",
        "system_summary": "hybrid plant containing ammonia plant and electrolyzer",
        "driver_config": driver_config_fname,
        "technology_config": tech_config,
        "plant_config": plant_config_fname,
    }

    # Create a H2Integrate model
    model = H2IntegrateModel(input_config)

    # Run the model
    model.run()
