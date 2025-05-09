from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a H2Integrate model
gh = H2IntegrateModel("08_onshore_steel_mn.yaml")

# Run the model
gh.run()

gh.post_process()
