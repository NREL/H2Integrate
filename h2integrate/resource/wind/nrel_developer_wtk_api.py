import urllib.parse
from typing import ClassVar
from pathlib import Path

import pandas as pd
from attrs import field, define

from h2integrate.core.validators import range_val
from h2integrate.resource.resource_base import ResourceBaseAPIConfig
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


class WTKNRELDeveloperAPIModel(WindResourceBaseAPIModel):
    def setup(self):
        super().setup()
        # initialize inputs for config
        # site_config = self.site_config = self.options["plant_config"]["site"]
        # sim_config = self.options["plant_config"]["plant"]["simulation"]
        resource_specs = self.options["resource_config"][
            "resource_parameters"
        ]  # TODO: update based on handling in H2IModel
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

        # check what steps to do
        self.get_data()

        # TODO: add inputs/outputs

    def create_filename(self):
        # TODO: update to handle multiple years
        filename = (
            f"{self.config.latitude}_{self.config.longitude}_{self.config.resource_year}_"
            f"{self.config.dataset_desc}_{self.interval}min_utc{self.config.timezone}.csv"
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
        header = pd.read_csv(fpath, nrows=1, header=None).values
        data = data.dropna(axis=1, how="all")
        return header, data

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pass
