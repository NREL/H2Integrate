import urllib.parse
from typing import ClassVar
from pathlib import Path

import pandas as pd
from attrs import field, define

from h2integrate.core.validators import range_val
from h2integrate.resource.resource_base import ResourceBaseAPIConfig
from h2integrate.resource.utilities.time_tools import make_time_profile, roll_timeseries_data
from h2integrate.resource.solar.solar_resource_base import SolarResourceBaseAPIModel
from h2integrate.resource.utilities.nrel_developer_api_keys import (
    get_nrel_developer_api_key,
    get_nrel_developer_api_email,
)


@define
class GOESNRELDeveloperAPIConfig(ResourceBaseAPIConfig):
    resource_year: int = field(converter=int, validator=range_val(1998, 2024))
    dataset_desc: str = "goes_aggregated_v4"
    resource_type: str = "solar"
    valid_intervals: ClassVar = [30, 60]
    resource_data: dict | object = field(default={})
    resource_filename: Path | str = field(default="")
    resource_dir: Path | str | None = field(default=None)


class GOESNRELDeveloperAPISolarResource(SolarResourceBaseAPIModel):
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
        self.config = GOESNRELDeveloperAPIConfig.from_dict(resource_specs)

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
        time_str = [
            data["time"][i].strftime("%m/%d/%Y %H:%M:%S (%z)") for i in range(len(data["time"]))
        ]
        data["time"] = time_str
        # self.data = data
        # TODO: remove ["Year", "Month", "Day", "Hour", "Minute"] from outputs
        self.add_discrete_output(
            "solar_resource_data", val=data, desc="Dict of solar resource data"
        )

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
        base_url = "https://developer.nrel.gov/api/nsrdb/v2/solar/nsrdb-GOES-aggregated-v4-0-0-download.csv?"
        url = base_url + urllib.parse.urlencode(input_data, True)
        return url

    def load_data(self, fpath):
        data = pd.read_csv(fpath, header=2)
        header = pd.read_csv(fpath, nrows=2, header=None)
        header_keys = header.iloc[0].to_list()
        header_vals = header.iloc[1].to_list()
        header_dict = dict(zip(header_keys, header_vals))

        time_cols = ["Year", "Month", "Day", "Hour", "Minute"]
        data_cols = [c for c in data.columns.to_list() if c not in time_cols]
        colnames_to_units = {
            c: header_dict[f"{c} Units"] for c in data_cols if f"{c} Units" in header_dict
        }
        # data_missing_units = [c for c in data_cols if f"{c} Units" not in header_dict]

        colname_mapper = {c: f"{c} ({v})" for c, v in colnames_to_units.items()}

        site_data = {
            "id": int(header_dict["Location ID"]),
            "site_tz": float(header_dict["Local Time Zone"]),
            "data_tz": float(header_dict["Time Zone"]),
            "site_lat": float(header_dict["Latitude"]),
            "site_lon": float(header_dict["Longitude"]),
            "elevation": float(header_dict["Elevation"]),
        }

        data = data.dropna(axis=1, how="all")
        data = data.rename(columns=colname_mapper)  # add units to colnames
        data_time_profile = self.make_data_time_profile(data, site_data["data_tz"])
        # dont include data that doesnt have units
        data_main_cols = time_cols + list(colname_mapper.values())
        # make units for data in openmdao-compatible units
        data, data_units = self.format_timeseries_data(data[data_main_cols])
        # convert units to standard units
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
            new_c = (
                new_c.replace(f"({units})", "").strip().replace(" ", "_").replace("__", "_").lower()
            )

            if units == "c":
                units = units.upper()
            if units == "w/m2":
                units = "W/m**2"
            if units == "nan" or units == "%":
                units = "percent"
            if units == "Degree" or units == "Degrees":
                units = "deg"

            data_rename_mapper.update({c: new_c})
            data_units.update({new_c: units})
        data = data.rename(columns=data_rename_mapper)
        return data, data_units

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pass
