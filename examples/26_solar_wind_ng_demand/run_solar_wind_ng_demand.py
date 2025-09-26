from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create an H2I model
h2i = H2IntegrateModel("solar_wind_ng_demand.yaml")

# Run the model
h2i.run()

# Post-process the results
h2i.post_process()
