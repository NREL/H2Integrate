from h2integrate.core.h2integrate_model import H2IntegrateModel
from h2integrate.resource.get_wind_data import fetch_and_save_wind_data


fetch_and_save_wind_data(
    source="open-meteo",
    year=2023,
    height=100,
    latitude=47.5233,
    longitude=-92.5366,
    turbulence_intensity=0.1,
    elevation=439.0,
    output="wind_resource.csv",
)

# Create a GreenHEART model
h2i_model = H2IntegrateModel("./wind_plant_electrolyzer.yaml")

# Run the model
h2i_model.run()

# Post-process the results
h2i_model.post_process()
