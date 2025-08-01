from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a H2Integrate model
model = H2IntegrateModel("12_ammonia_synloop.yaml")

# Run the model
model.run()

model.post_process()
