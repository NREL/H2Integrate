from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a GreenHEART model
h2i_model = H2IntegrateModel("wind_plant_electrolyzer.yaml")

# Run the model
h2i_model.run()

# Post-process the results
# h2i_model.post_process()
