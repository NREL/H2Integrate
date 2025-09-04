from typing import ClassVar
from pathlib import Path

import openmdao.api as om
from attrs import field, define
from rex.sam_resource import SAMResource

from h2integrate.core.utilities import BaseConfig
from h2integrate.resource.utilities.file_tools import check_resource_dir
from h2integrate.resource.utilities.download_tools import download_from_api


@define
class ResourceBaseAPIConfig(BaseConfig):
    latitude: float = field()
    longitude: float = field()

    # TODO: should resource year be allowed to be a list of years?
    # resource_year: int = field(converter=int)

    # dt: int | float = field()
    # n_timesteps: int = field(converter=int)
    timezone: int | float = field()
    # start_time: str

    # resource_data: dict | object = field(default={})
    # resource_filename: Path | str = field(default="")
    # resource_dir: Path | str | None = field(default=None)

    dataset_desc: str = "default"
    resource_type: str = "none"
    valid_intervals: ClassVar = [60]


class ResourceBaseAPIModel(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("resource_config", types=dict)
        self.options.declare("driver_config", types=dict)

    def setup(self):
        self.site_config = self.options["plant_config"]["site"]
        self.sim_config = self.options["plant_config"]["plant"]["simulation"]
        self.n_timesteps = int(self.sim_config["n_timesteps"])
        self.dt = self.sim_config["dt"]
        self.start_time = self.sim_config["start_time"]
        # resource_specs = self.options["resource_config"][
        #     "resource_parameters"
        # ]  # TODO: update based on handling in H2IModel
        # resource_specs.setdefault("latitude", site_config["latitude"])
        # resource_specs.setdefault("longitude", site_config["longitude"])
        # resource_specs.setdefault(
        #     "resource_dir", site_config["resources"].get("resource_dir", None)
        # )

        # resource_specs.setdefault("timezone", sim_config.get("timezone"))
        # resource_specs.setdefault("dt", sim_config.get("dt"))
        # resource_specs.setdefault("n_timesteps", sim_config.get("n_timesteps"))

        # resource_specs.setdefault("start_time", sim_config.get("start_time"))

        # self.config = ResourceBaseAPIConfig.from_dict(resource_specs)

        # TODO: add outputs

    # TODO: add functions with not implemented errors
    def create_filename(self):
        raise NotImplementedError("This method should be implemented in a subclass.")

    def create_url(self):
        raise NotImplementedError("This method should be implemented in a subclass.")

    def download_data(self, url, fpath):
        success = download_from_api(url, fpath)
        return success

    def load_data(self, fpath):
        raise NotImplementedError("This method should be implemented in a subclass.")

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        raise NotImplementedError("This method should be implemented in a subclass.")

    def roll_data_for_timezone(self, data: dict, tz_to: int | float, tz_from: int | float):
        n_dt_per_hour = 3600 // self.dt
        tz_shift = tz_from + tz_to
        for var, timeseries_data in data.items():
            data[var] = SAMResource.roll_timeseries((timeseries_data), int(tz_shift), n_dt_per_hour)

    def get_data(self):
        data = None

        # 1) check if user provided data
        if bool(self.config.resource_data):
            # check that data has correct interval and timezone
            data = self.config.resource_data
            return data

        # 2) check if user provided directory or filename
        if data is None:
            provided_filename = False if self.config.resource_filename == "" else True
            provided_dir = False if self.config.resource_dir is None else True
            if (
                provided_dir
                and Path(self.config.resource_data).parts[-1] == self.config.resource_type
            ):
                resource_dir = check_resource_dir(resource_dir=self.config.resource_dir)
            else:
                resource_dir = check_resource_dir(
                    resource_dir=self.config.resource_dir, resource_subdir=self.config.resource_type
                )
            if provided_filename:
                filepath = resource_dir / self.config.resource_filename
            else:
                filename = self.create_filename()
                filepath = resource_dir / filename
            if filepath.is_file():
                data = self.load_data(filepath)
                return data

        # 3) download data if not found in file or not provided
        if data is None:
            url = self.create_url()
            success = self.download_data(url, filepath)
            if not success:
                raise ValueError("Did not successfully download data")
            data = self.load_data(filepath)
            return data

        if data is None:
            raise ValueError("Unexpected situation occurred while trying to load data")
