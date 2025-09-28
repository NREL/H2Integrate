import urllib.parse
from pathlib import Path

import pandas as pd
from attrs import field, define

from h2integrate.core.validators import range_val
from h2integrate.resource.resource_base import ResourceBaseAPIConfig
from h2integrate.resource.solar.solar_resource_base import SolarResourceBaseAPIModel
from h2integrate.resource.utilities.nrel_developer_api_keys import (
    get_nrel_developer_api_key,
    get_nrel_developer_api_email,
)


@define
class GOESNRELDeveloperAPIConfig(ResourceBaseAPIConfig):
    """Configuration class to download wind resource data from
    `GOES Aggregated PSM v4 <https://developer.nrel.gov/docs/solar/nsrdb/nsrdb-GOES-aggregated-v4-0-0-download/>`_.

    Args:
        resource_year (int): Year to use for resource data.
            Must been between 1998 and 2024 (inclusive).
        resource_data (dict | object, optional): Dictionary of user-input resource data.
            Defaults to an empty dictionary.
        resource_dir (str | Path, optional): Folder to save resource files to or
            load resource files from. Defaults to "".
        resource_filename (str, optional): Filename to save resource data to or load
            resource data from. Defaults to None.

    Attributes:
        dataset_desc (str): description of the dataset, used in file naming.
            For this dataset, the `dataset_desc` is "goes_aggregated_v2".
        resource_type (str): type of resource data downloaded, used in folder naming.
            For this dataset, the `resource_type` is "solar".
        valid_intervals (list[int]): time interval(s) in minutes that resource data can be
            downloaded in. For this dataset, `valid_intervals` are 30 and 60 minutes.

    """

    resource_year: int = field(converter=int, validator=range_val(1998, 2024))
    dataset_desc: str = "goes_aggregated_v4"
    resource_type: str = "solar"
    valid_intervals: list[int] = field(factory=lambda: [30, 60])
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
        resource_specs.setdefault("timezone", self.sim_config.get("timezone", 0))
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

        # check what steps to do
        data = self.get_data()

        # NOTE: add any upsampling or downsampling, this should be done here
        self.add_discrete_output(
            "solar_resource_data", val=data, desc="Dict of solar resource data"
        )

    def create_filename(self):
        """Create default filename to save downloaded data to. Filename is formatted as
        "{latitude}_{longitude}_{resource_year}_goes_aggregated_v4_{interval}min_{tz_desc}_tz.csv"
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
            "filepath": str(fpath),
        }

        data = data.dropna(axis=1, how="all")
        data = data.rename(columns=colname_mapper)  # add units to colnames

        # dont include data that doesnt have units
        data_main_cols = time_cols + list(colname_mapper.values())
        # make units for data in openmdao-compatible units
        data, data_units = self.format_timeseries_data(data[data_main_cols])
        # convert units to standard units
        data, data_units = self.compare_units_and_correct(data, data_units)

        data.update(site_data)
        return data

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
        # time_cols_mapper = {t: t.lower() for t in time_cols}
        # data = data.rename(columns=time_cols_mapper)
        data_dict = {c: data[c].astype(float).values for x, c in data_rename_mapper.items()}
        data_time_dict = {c.lower(): data[c].astype(float).values for c in time_cols}
        data_dict.update(data_time_dict)
        return data_dict, data_units

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pass
