from pathlib import Path

import openmdao.api as om
from attrs import field, define
from hopp.utilities.keys import (
    set_nrel_key_dot_env,
    get_developer_nrel_gov_key,
    get_developer_nrel_gov_email,
)
from PySAM.ResourceTools import SAM_CSV_to_solar_data

from h2integrate import ROOT_DIR
from h2integrate.core.utilities import BaseConfig
from h2integrate.core.validators import contains, range_val
from h2integrate.resource.api_tools import download_from_api
from h2integrate.resource.dataset_tools import pull_solar_resource


@define
class SolarResourceConfig(BaseConfig):
    """Configuration class for solar resource data.

    Attributes:
        latitude (float): Latitude of wind plant location.
        longitude (float): Longitude of wind plant location.
        resource_year (int): Year for resource data. Must be between 1998 and 2024.
        interval (int): timestep for solar resource data in minutes. Must be either 30 or 60.
        resource_origin (str): Whether to download data using the API or pull from a dataset.
            - 'API': if needed, download resource data from the API
            - 'HPC': if needed, pull data from a dataset
        resource_data (dict | object): If dict, dict should contain solar resource data. If object,
            the object must have 'data' attribute that returns a dict of solar resource data.
        resource_filepath (str | Path): Filename or filepath of file containing solar resource data.
            Used if reading data from a csv file or downloading from API. Defaults to "".
        resource_dir (str | Path): Directory containing solar resource data file(s).
            Used if reading data from a csv file or downloading from API. Defaults to "".
        data_in_utc (bool): If True, return data in UTC. If False, return data in local timezone.
            Defaults to False.

        base_url (str): base of URL to use for API downloads. Defaults to
            'https://developer.nrel.gov/api/nsrdb/v2/solar/nsrdb-GOES-aggregated-v4-0-0-download.csv'
        dataset_dir (str): directory of solar resource dataset, only used if resource_origin=='HPC'.
            Defaults to file location on Kestrel which is '/datasets/NSRDB/current'.

    """

    latitude: float = field()
    longitude: float = field()
    resource_year: int = field(converter=int, validator=range_val(1998, 2024))
    interval: int = field(converter=int, validator=contains([30, 60]))

    resource_origin: str = field(
        converter=(str.strip, str.upper), validator=contains(["API", "HPC"])
    )
    resource_data: dict | object = field(default={})
    resource_filepath: Path | str = field(default="")
    resource_dir: Path | str = field(default="")

    data_in_utc: bool = field(default=False)

    base_url: str = field(
        default="https://developer.nrel.gov/api/nsrdb/v2/solar/nsrdb-GOES-aggregated-v4-0-0-download.csv"
    )
    dataset_dir: str = field(default="/datasets/NSRDB/current")

    use_api = False
    use_dataset = False

    def __attrs_post_init__(self):
        # user provided dictionary of resource data
        if isinstance(self.resource_data, (dict, object)):
            if isinstance(self.resource_data, dict):
                if bool(self.resource_data):
                    return
            else:
                # user provided object of resource data that has attribute "data" as dictionary
                data = self.resource_data.data
                if bool(data):
                    return

        # user did not provide resource data and using API call
        if self.resource_origin == "API":
            if Path(self.resource_filepath).is_file():
                # user provided filepath and file exists
                self.resource_dir = Path(self.resource_filepath).parent
                return
            if not self.resource_dir.is_dir():
                if "solar" not in Path(self.resource_dir).parts:
                    Path.mkdir(Path(self.resource_dir) / "solar")
                else:
                    Path.mkdir(Path(self.resource_dir))

            if str(self.resource_dir) == "":
                self.resource_dir = ROOT_DIR / "resource_files" / "solar"

            filename = (
                f"{self.latitude}_{self.longitude}_psmv4_{self.interval}_{self.resource_year}.csv"
            )

            if (Path(self.resource_dir) / filename).is_file():
                return

            self.resource_filepath = Path(self.resource_dir) / filename
            self.use_api = True
        else:
            self.use_dataset = True


class SolarResource(om.ExplicitComponent):
    """_summary_

    Returns:
        Required data containing

        - **year**
        - **month**
        - **hour**
        - **day**
        - **minute**
        - **dn**
        - **df**
        - **tdry**
        - **wspd**

    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)
        self.options.declare("driver_config", types=dict)

    def setup(self):
        site_config = self.site_config = self.options["plant_config"]["site"]

        solar_resource_specs = site_config["resources"]["solar_resource"]
        solar_resource_specs.setdefault("latitude", site_config["latitude"])
        solar_resource_specs.setdefault("longitude", site_config["longitude"])
        solar_resource_specs.setdefault(
            "resource_origin", site_config["resources"].get("resource_origin", None)
        )

        if solar_resource_specs["resource_origin"] == "API":
            solar_resource_specs.setdefault(
                "resource_dir", site_config["resources"].get("resource_dir", "")
            )

        self.config = SolarResourceConfig.from_dict(solar_resource_specs)

        self.required_data = [
            "lat",
            "lon",
            "tz",
            "elev",
            "year",
            "month",
            "day",
            "hour",
            "minute",
            "dn",
            "df",
            "tdry",
            "wspd",
        ]
        self.optional_data = ["gh", "wdir", "pres", "tdew", "rhum", "alb", "snow"]
        self.units_for_data = {
            "year": "year",
            "month": "month",
            "day": "d",
            "hour": "h",
            "minute": "min",
            "dn": "W/m**2",
            "df": "W/m**2",
            "tdry": "degC",
            "wspd": "m/s",
            "gh": "W/m**2",
            "wdir": "deg",
            "pres": "mbar",
            "tdew": "degC",
            "rhum": "unitless",
            "alb": "unitless",
            "snow": "cm",
        }

        resource_data = None
        if not self.config.use_api and not self.config.use_dataset:
            if isinstance(self.config.resource_data, dict):
                if bool(self.config.resource_data):
                    resource_data = self.config.resource_data
            else:
                resource_data = self.config.resource_data.data
            if resource_data is None and Path(self.config.resource_filepath).is_file():
                resource_data = SAM_CSV_to_solar_data(self.config.resource_filepath)

        if self.config.use_api:
            try:
                get_developer_nrel_gov_email()
            except ValueError:
                set_nrel_key_dot_env()

            url = (
                f"{self.config.base_url}?wkt=POINT({self.config.longitude}+{self.config.latitude})&names={self.config.resource_year}"
                f"&interval={self.config.interval}&utc={str(self.config.data_in_utc).lower()}&email={get_developer_nrel_gov_email()}"
                f"&api_key={get_developer_nrel_gov_key()}"
            )
            download_from_api(url, self.config.resource_filepath)
            resource_data = SAM_CSV_to_solar_data(self.config.resource_filepath)
            # TODO: add check to adjust timezone
        if self.config.use_dataset:
            dataset_fpath = Path(self.config.dataset_dir) / f"nsrdb_{self.config.resource_year}.h5"
            if not dataset_fpath.is_file():
                raise FileNotFoundError(f"{dataset_fpath} was not found")
            resource_data = pull_solar_resource(
                dataset_fpath,
                self.config.latitude,
                self.config.longitude,
                self.config.interval,
                self.config.data_in_utc,
            )

        for required_key in self.required_data:
            if required_key not in resource_data:
                raise ValueError(f"Solar resource data is missing {required_key}")

        for data_key, data_val in resource_data.items():
            if data_key in self.units_for_data:
                self.add_output(data_key, val=data_val, units=self.units_for_data[data_key])
        if self.config.data_in_utc:
            self.add_discrete_output(
                "solar_data_tz", val=0, desc="Timezone for solar resource data"
            )
        else:
            self.add_discrete_output(
                "solar_data_tz",
                val=int(resource_data["tz"]),
                desc="Timezone for solar resource data",
            )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pass
