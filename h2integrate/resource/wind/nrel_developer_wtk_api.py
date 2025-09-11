import urllib.parse
from typing import ClassVar
from pathlib import Path

import pandas as pd
from attrs import field, define

from h2integrate.core.validators import range_val
from h2integrate.resource.resource_base import ResourceBaseAPIConfig
from h2integrate.resource.utilities.time_tools import make_time_profile, roll_timeseries_data
from h2integrate.resource.wind.wind_resource_base import WindResourceBaseAPIModel
from h2integrate.resource.utilities.nrel_developer_api_keys import (
    get_nrel_developer_api_key,
    get_nrel_developer_api_email,
)


@define
class WTKNRELDeveloperAPIConfig(ResourceBaseAPIConfig):
    """Configuration class to download wind resoure data from
    `Wind Toolkit Data V2 <https://developer.nrel.gov/docs/wind/wind-toolkit/wtk-download/>`_.

    Args:
        resource_year (int): Year to use for resource data.
            Must been between 2007 and 2014 (inclusive).
        resource_data (dict | object, optional): Dictionary of user-input resource data.
            Defaults to an empty dictionary.
        resource_dir (str | Path, optional): Folder to save resource files to or
            load resource files from. Defaults to "".
        resource_filename (str, optional): Filename to save resource data to or load
            resource data from. Defaults to None.

    Attributes:
        dataset_desc (str): description of the dataset, used in file naming.
            For this dataset, the `dataset_desc` is "wtk_v2".
        resource_type (str): type of resource data downloaded, used in folder naming.
            For this dataset, the `resource_type` is "wind".
        valid_intervals (list[int]): time interval(s) in minutes that resource data can be
            downloaded in. For this dataset, `valid_intervals` are 5, 15, 30, and 60 minutes.

    """

    resource_year: int = field(converter=int, validator=range_val(2007, 2014))
    dataset_desc: str = "wtk_v2"
    resource_type: str = "wind"
    valid_intervals: ClassVar = [5, 15, 30, 60]
    resource_data: dict | object = field(default={})
    resource_filename: Path | str = field(default="")
    resource_dir: Path | str | None = field(default=None)


class WTKNRELDeveloperAPIWindResource(WindResourceBaseAPIModel):
    def setup(self):
        super().setup()

        # create the input dictionary for WTKNRELDeveloperAPIConfig
        resource_specs = self.options["resource_config"]
        # set the default latitude, longitude, and resource_year from the site_config
        resource_specs.setdefault("latitude", self.site_config["latitude"])
        resource_specs.setdefault("longitude", self.site_config["longitude"])
        resource_specs.setdefault("resource_year", self.site_config.get("year", None))

        # set the default resource_dir from a directory that can be
        # specified in site_config['resources']['resource_dir']
        resource_specs.setdefault(
            "resource_dir", self.site_config["resources"].get("resource_dir", None)
        )

        # set the timezone as the simulation config timezone
        if "timezone" in resource_specs:
            msg = (
                "The timezone cannot be specified for a specific resource. "
                "The timezone is set in the plant_config['plant']['simulation']['timezone']."
            )

            raise ValueError(msg)
        resource_specs.setdefault("timezone", self.sim_config.get("timezone"))

        # create the resource config
        self.config = WTKNRELDeveloperAPIConfig.from_dict(resource_specs)

        # set UTC variable depending on timezone, used for filenaming
        self.utc = False
        if float(self.config.timezone) == 0.0:
            self.utc = True

        # check interval to use for data download/load based on simulation timestep
        interval = self.dt / 60
        if any(float(v) == float(interval) for v in self.config.valid_intervals):
            self.interval = int(interval)
        else:
            if interval > max(self.config.valid_intervals):
                self.interval = int(max(self.config.valid_intervals))
            else:
                self.interval = int(min(self.config.valid_intervals))

        # create the desired time profile for the resource data
        self.resource_time_profile = make_time_profile(
            self.start_time,
            self.dt,
            self.n_timesteps,
            self.config.timezone,
            self.config.resource_year,
        )

        # get the data dictionary
        data = self.get_data()

        # NOTE: add any upsampling or downsampling, this should be done here

        # roll the data to the resource_time_profile
        data = roll_timeseries_data(self.resource_time_profile, data["time"], data, self.dt)

        # convert the time profile to a list of strings to be JSON-compatible
        time_str = [
            data["time"][i].strftime("%m/%d/%Y %H:%M:%S (%z)") for i in range(len(data["time"]))
        ]
        data["time"] = time_str

        # add resource data dictionary as an out
        self.add_discrete_output("wind_resource_data", val=data, desc="Dict of wind resource data")

    def create_filename(self):
        """Create default filename to save downloaded data to. Filename is formatted as
        "{latitude}_{longitude}_{resource_year}_wtk_v2_{interval}min_{tz_desc}_tz.csv"
        where "tz_desc" is "utc" if the timezone is zero, or "local" otherwise.

        Returns:
            str: filename for resource data to be saved to or loaded from.
        """
        # TODO: update to handle multiple years
        # TODO: update to handle nonstandard time intervals
        if self.utc:
            tz_desc = "utc"
        else:
            tz_desc = "local"
        filename = (
            f"{self.config.latitude}_{self.config.longitude}_{self.config.resource_year}_"
            f"{self.config.dataset_desc}_{self.interval}min_{tz_desc}_tz.csv"
        )
        return filename

    def create_url(self):
        """Create url for data download.

        Returns:
            str: url to use for API call.
        """
        input_data = {
            "wkt": f"POINT({self.config.longitude} {self.config.latitude})",
            "names": [str(self.config.resource_year)],  # TODO: update to handle multiple years
            "interval": str(self.interval),
            "utc": str(self.utc).lower(),
            "api_key": get_nrel_developer_api_key(),
            "email": get_nrel_developer_api_email(),
        }
        base_url = "https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-download.csv?"
        url = base_url + urllib.parse.urlencode(input_data, True)
        return url

    def load_data(self, fpath):
        """Load data from a file and format as a dictionary that:

        1) follows naming convention described in WindResourceBaseAPIModel.
        2) is converted to standardized units described in WindResourceBaseAPIModel.

        This method does the following steps:

        1) load the data, separate out scalar data and timeseries data
        2) remove unused data
        3) make a time profile for the data, set as the 'time' key for the output data.
            Calls `make_data_time_profile()` method.
        4) Rename the data columns to standardized naming convention and create dictionary of
            OpenMDAO compatible units for the data. Calls `format_timeseries_data()` method.
        5) Convert data to stadardized units. Calls `compare_units_and_correct()` method

        Args:
            fpath (str | Path): filepath to file containing the data

        Returns:
            dict: dictionary of data in standardized units and naming convention.
            Time information is found in the 'time' key.
        """

        data = pd.read_csv(fpath, header=1)
        header = pd.read_csv(fpath, nrows=1, header=None).values[0]
        header_keys = header[0 : len(header) : 2]
        header_vals = header[1 : len(header) : 2]
        header_dict = dict(zip(header_keys, header_vals))
        site_data = {
            "id": header_dict["SiteID"],
            "site_tz": header_dict["Site Timezone"],
            "data_tz": header_dict["Data Timezone"],
            "site_lat": header_dict["Latitude"],
            "site_lon": header_dict["Longitude"],
        }

        data = data.dropna(axis=1, how="all")
        data_time_profile = self.make_data_time_profile(data, site_data["data_tz"])
        data, data_units = self.format_timeseries_data(data)
        # make units for data in openmdao-compatible units
        data_units = {
            k: v.replace("%", "percent").replace("degrees", "deg").replace("hour", "h")
            for k, v in data_units.items()
        }
        data, data_units = self.compare_units_and_correct(data, data_units)
        time_cols = ["Year", "Month", "Day", "Hour", "Minute"]
        timeseries_data = {c: data[c].values for c in data.columns.to_list() if c not in time_cols}
        timeseries_data.update({"time": data_time_profile})
        timeseries_data.update(site_data)
        return timeseries_data

    def make_data_time_profile(self, data, data_tz):
        """Create time profile corresponding the data.

        Args:
            data (pd.DataFrame): Dataframe of timeseries data.
                Must have columns of "Year", "Month", "Day", "Hour", and "Minute".

            data_tz (int | float): timezone that the data is in.

        Returns:
            list[datetime.datetime]: time profile of data.
        """
        data_start_time_dict = data.iloc[0][["Year", "Month", "Day", "Hour", "Minute"]].to_dict()
        data_t0 = {k: int(v) for k, v in data_start_time_dict.items()}
        data_time_profile = pd.to_datetime(data[["Year", "Month", "Day", "Hour", "Minute"]])
        data_ntimesteps = len(data)
        data_start_dmy = f"{data_t0['Month']:02d}/{data_t0['Day']:02d}/{data_t0['Year']:02d}"
        data_start_hms = f"{data_t0['Hour']:02d}:{data_t0['Minute']:02d}:00"
        data_start_time = f"{data_start_dmy} {data_start_hms}"
        data_dt = data_time_profile[1] - data_time_profile[0]
        data_time_profile = make_time_profile(
            data_start_time, data_dt.seconds, data_ntimesteps, data_tz, start_year=None
        )
        return data_time_profile

    def format_timeseries_data(self, data):
        """Convert data to a dictionary with keys that follow the standardized naming convention and
        create a dictionary containing the units for the data.

        Args:
            data (pd.DataFrame): Dataframe of timeseries data.

        Returns:
            2-element tuple containing

            - **data** (*dict*): data dictionary with keys following the standardized naming
                convention.
            - **data_units** (*dict*): dictionary with same keys as `data` and values as the
                data units in OpenMDAO compatible format.
        """
        time_cols = ["Year", "Month", "Day", "Hour", "Minute"]
        data_cols_init = [c for c in data.columns.to_list() if c not in time_cols]
        data_rename_mapper = {}
        data_units = {}
        for c in data_cols_init:
            units = c.split("(")[-1].strip(")")
            new_c = c.replace("air", "").replace("at ", "")
            new_c = new_c.replace(f"({units})", "").strip().replace(" ", "_").replace("__", "_")

            if "surface" in c:
                new_c += "_0m"
                new_c = new_c.replace("surface", "").replace("__", "").strip("_")
            data_rename_mapper.update({c: new_c})
            data_units.update({new_c: units})
        data = data.rename(columns=data_rename_mapper)
        return data, data_units

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pass
