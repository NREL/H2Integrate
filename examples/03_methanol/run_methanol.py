from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create an H2I model
h2i = H2IntegrateModel("03_methanol.yaml")

# Run the model
h2i.run()

h2i.post_process()
