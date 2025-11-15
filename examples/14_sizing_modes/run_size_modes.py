from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a H2Integrate model
model = H2IntegrateModel("14_size_mode.yaml")
model.technology_config["technologies"]["electrolyzer"]["model_inputs"]["performance_parameters"][
    "sizing"
] = {
    "size_mode": "resize_by_max_commodity",
    "resize_by_flow": "hydrogen",
    "max_commodity_ratio": 1.0,
}
model.plant_config["technology_interconnections"].append(
    ["ammonia", "electrolyzer", "max_hydrogen_capacity"]
)
model.setup()
# Run the model
model.run()

model.post_process()
