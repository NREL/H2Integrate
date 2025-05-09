from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a H2Integrate model
gh = H2IntegrateModel("02_texas_ammonia.yaml")

# Run the model
gh.run()

gh.post_process()
