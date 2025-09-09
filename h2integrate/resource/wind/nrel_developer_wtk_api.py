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

        resource_specs = self.options["resource_config"]
        resource_specs.setdefault("latitude", self.site_config["latitude"])
        resource_specs.setdefault("longitude", self.site_config["longitude"])
        resource_specs.setdefault("resource_year", self.site_config.get("year", None))
        resource_specs.setdefault(
            "resource_dir", self.site_config["resources"].get("resource_dir", None)
        )
        resource_specs.setdefault("timezone", self.sim_config.get("timezone"))
        self.config = WTKNRELDeveloperAPIConfig.from_dict(resource_specs)

        self.utc = False
        if float(self.config.timezone) == 0.0:
            self.utc = True

        interval = self.dt / 60
        if any(float(v) == float(interval) for v in self.config.valid_intervals):
            self.interval = int(interval)
        else:
            if interval > max(self.config.valid_intervals):
                self.interval = int(max(self.config.valid_intervals))
            else:
                self.interval = int(min(self.config.valid_intervals))

        self.resource_time_profile = make_time_profile(
            self.start_time,
            self.dt,
            self.n_timesteps,
            self.config.timezone,
            self.config.resource_year,
        )
        # check what steps to do
        data = self.get_data()

        # NOTE: add any upsampling or downsampling, this should be done here
        data = roll_timeseries_data(self.resource_time_profile, data["time"], data, self.dt)
        self.data = data
        self.add_discrete_output("wind_resource_data", val=data, desc="Dict of wind resource data")

    def create_filename(self):
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
        timeseries_data = {c: data[c].values for c in data.columns.to_list()}
        timeseries_data.update({"time": data_time_profile})
        timeseries_data.update(site_data)
        return timeseries_data

    def make_data_time_profile(self, data, data_tz):
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
