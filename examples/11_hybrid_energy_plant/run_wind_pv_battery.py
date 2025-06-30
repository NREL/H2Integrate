from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a GreenHEART model
gh = H2IntegrateModel("wind_pv_battery.yaml")

# Run the model
gh.run()

gh.post_process()
