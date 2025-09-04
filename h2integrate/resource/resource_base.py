from typing import ClassVar
from pathlib import Path

import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig
from h2integrate.core.validators import range_val


@define
class ResourceBaseAPIConfig(BaseConfig):
    latitude: float = field()
    longitude: float = field()

    # TODO: should resource year be allowed to be a list of years?
    resource_year: int = field(converter=int, validator=range_val(1800, 2100))

    # dt: int | float = field()
    # n_timesteps: int = field(converter=int)
    timezone: int | float = field()
    # start_time: str

    resource_data: dict | object = field(default={})

    resource_filename: Path | str = field(default="")
    resource_dir: Path | str | None = field(default=None)

    dataset_desc: str = "default"
    resource_type: str = "none"
    valid_intervals: ClassVar = [60]


class ResourceBaseAPIModel(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("resource_config", types=dict)
        self.options.declare("driver_config", types=dict)

    def setup(self):
        site_config = self.site_config = self.options["plant_config"]["site"]
        sim_config = self.sim_config = self.options["plant_config"]["plant"]["simulation"]
        self.n_timesteps = int(self.sim_config["n_timesteps"])
        self.dt = self.sim_config["dt"]
        self.start_time = self.sim_config["start_time"]
        resource_specs = self.options["resource_config"][
            "resource_parameters"
        ]  # TODO: update based on handling in H2IModel
        resource_specs.setdefault("latitude", site_config["latitude"])
        resource_specs.setdefault("longitude", site_config["longitude"])
        resource_specs.setdefault(
            "resource_dir", site_config["resources"].get("resource_dir", None)
        )

        resource_specs.setdefault("timezone", sim_config.get("timezone"))
        # resource_specs.setdefault("dt", sim_config.get("dt"))
        # resource_specs.setdefault("n_timesteps", sim_config.get("n_timesteps"))

        # resource_specs.setdefault("start_time", sim_config.get("start_time"))

        # self.config = ResourceBaseAPIConfig.from_dict(resource_specs)

        # TODO: add outputs

    # TODO: add functions with not implemented errors
    def download_data(self, url, fpath):
        pass

    def load_data(self, fpath):
        pass

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pass
