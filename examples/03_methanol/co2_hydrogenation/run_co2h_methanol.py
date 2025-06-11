from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create an H2I model
h2i = H2IntegrateModel("03_co2h_methanol.yaml")

# Size the components
h2_kgpy = h2i.plant.methanol.co2h_methanol_plant_performance.size()
h2_MW = h2_kgpy * 55 / 8760 / 1000
h2i.technology_config["technologies"]["electrolyzer"]["model_inputs"]["shared_parameters"][
    "rating"
] = h2_MW

# Run the model
h2i.run()

h2i.post_process()
