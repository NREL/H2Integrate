from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create an H2I model for natural geologic hydrogen production
h2i_nat = H2IntegrateModel("04_geo_h2_natural.yaml")

# Run the model
h2i_nat.run()
h2i_nat.post_process()


# Create an H2I model for stimulated geologic hydrogen production
h2i_stim = H2IntegrateModel("04_geo_h2_stimulated.yaml")

# Run the model
h2i_stim.run()
h2i_stim.post_process()
