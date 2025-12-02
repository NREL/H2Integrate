from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create the model
h2i_model = H2IntegrateModel("./h2i_inputs/wind_pv_battery.yaml")

# Run the model
h2i_model.run()

# Post-process the results
h2i_model.post_process()
