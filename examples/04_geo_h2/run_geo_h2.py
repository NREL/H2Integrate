from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create an H2I model - comment one out to choose natural or stimulated
h2i = H2IntegrateModel("04_geo_h2_natural.yaml")
h2i = H2IntegrateModel("04_geo_h2_stimulated.yaml")

# Run the model
h2i.run()

h2i.post_process()
