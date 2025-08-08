from pathlib import Path

import pandas as pd
import requests
import openmdao.api as om
from attrs import field, define, validators

from h2integrate.core.utilities import BaseConfig


class WindResource(om.ExplicitComponent):
    """
    A resource component for processing wind data from a CSV file or API call.

    Methods:
        initialize():
            Declares the options for the component, including the required "resource_config" option.
        setup():
            Defines the outputs for the component, including wind speed, direction, turbulence
            intensity, elevation, and height.
        compute(inputs, outputs):
            Reads, processes, and adjusts wind data based on the configuration.
    """

    def initialize(self):
        self.options.declare("resource_config", types=str)

    def setup(self):
        # Define inputs and outputs
        self.add_output("wind_speed", shape=8760, val=0.0, units="m/s")
        self.add_output(
            "wind_direction",
            shape=8760,
            val=0.0,
            units="deg",
            desc="zero degrees from the north increasing clock-wise",
        )
        self.add_output("turbulence_intensity", shape=1, val=0.0, units="unitless")
        self.add_output("elevation", shape=1, val=0.0, units="m", desc="elevation above sea level")
        self.add_output("height", shape=1, val=0.0, units="m", desc="height from ground level")

    def compute(self, inputs, outputs):
        # Get the resource configuration
        resource_config = self.options["resource_config"]
        file_path = Path(resource_config)

        # Check if the file exists
        if file_path.exists():
            # Load data from the file
            wind_data = pd.read_csv(file_path)
        else:
            # If the file does not exist, call the API to fetch data
            wind_api = WindAPI(self.options["resource_config"])
            wind_data = wind_api.fetch_data()

            # Save the fetched data to a file for future use
            wind_data.to_csv(file_path, index=False)

        # Extract configuration values
        config = self.options["resource_config"]
        desired_height = config.height
        turbulence_intensity = config.turbulence_intensity
        elevation = config.elevation

        # Adjust wind speed based on the desired height using a logarithmic wind profile
        reference_height = wind_data["height"].iloc[0]
        wind_data["wind_speed"] = wind_data["wind_speed"] * (desired_height / reference_height)

        # Assign outputs
        outputs["wind_speed"] = wind_data["wind_speed"].values
        outputs["wind_direction"] = wind_data["wind_direction"].values
        outputs["turbulence_intensity"] = turbulence_intensity
        outputs["elevation"] = elevation
        outputs["height"] = desired_height


@define
class WindAPIConfig(BaseConfig):
    """
    Configuration class for the WindAPI.

    Attributes:
        source (str): The API source to use ("open-meteo" or "nrel-rex").
        year (int): The year for which wind data is requested.
        height (int): The height above ground level for wind measurements (in meters).
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.
        turbulence_intensity (float): The turbulence intensity (unitless).
        elevation (float): The elevation above sea level (in meters).
        api_key (str | None): The API key for NREL Resource EXtraction Tool (REX)
                              (required if using "nrel-rex").
    """

    source: str = field(validator=validators.in_(["open-meteo", "nrel-rex"]))
    year: int = field()
    height: int = field()
    latitude: float = field()
    longitude: float = field()
    turbulence_intensity: float = field()
    elevation: float = field()
    api_key: str = field(default=None)  # Optional for Open-Meteo, required for NREL REX


class WindAPI:
    """
    A class to fetch wind resource data from either the Open-Meteo or NREL REX API.

    Methods:
        fetch_data():
            Fetches wind resource data from the specified API and returns it as a pandas DataFrame.
    """

    def __init__(self, config: WindAPIConfig):
        self.config = config

    def fetch_data(self):
        """
        Fetch wind resource data based on the specified source in the configuration.

        Returns:
            pd.DataFrame: A DataFrame containing wind resource data with columns:
                - wind_speed (m/s)
                - wind_direction (degrees)
                - height (m)
        """
        if self.config.source == "open-meteo":
            return self._fetch_open_meteo_data()
        elif self.config.source == "nrel-rex":
            return self._fetch_nrel_rex_data()
        else:
            raise ValueError(f"Unsupported source: {self.config.source}")

    def _fetch_open_meteo_data(self):
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.config.latitude,
            "longitude": self.config.longitude,
            "elevation": self.config.height,
            "year": self.config.year,
            "hourly": "wind_speed,wind_direction",
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        wind_speed = data["hourly"]["wind_speed"]
        wind_direction = data["hourly"]["wind_direction"]

        return pd.DataFrame(
            {
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "height": [self.config.height] * len(wind_speed),
            }
        )

    def _fetch_nrel_rex_data(self):
        if not self.config.api_key:
            raise ValueError("API key is required for NREL REX API.")

        url = "https://developer.nrel.gov/api/rex/v1/wind_data"
        params = {
            "api_key": self.config.api_key,
            "latitude": self.config.latitude,
            "longitude": self.config.longitude,
            "height": self.config.height,
            "year": self.config.year,
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        wind_speed = data["outputs"]["wind_speed"]
        wind_direction = data["outputs"]["wind_direction"]

        return pd.DataFrame(
            {
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "height": [self.config.height] * len(wind_speed),
            }
        )
