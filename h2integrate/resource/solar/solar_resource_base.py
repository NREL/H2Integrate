from attrs import define

from h2integrate.resource.resource_base import ResourceBaseAPIModel, ResourceBaseAPIConfig


@define
class SolarResourceBaseAPIConfig(ResourceBaseAPIConfig):
    # latitude: float = field()
    # longitude: float = field()
    # resource_year: int = field(converter=int, validator=range_val(1998, 2024))
    resource_type: str = "solar"

    # interval: int = field(converter=int, validator=contains([30, 60]))

    # resource_data: dict | object = field(default={})
    # resource_filepath: Path | str = field(default="")
    # resource_dir: Path | str = field(default="")

    # dataset_desc: str = "default"
    # pass


class SolarResourceBaseAPIModel(ResourceBaseAPIModel):
    def setup(self):
        self.resource_type = "solar"

        site_config = self.site_config = self.options["plant_config"]["site"]
        sim_config = self.options["plant_config"]["plant"]["simulation"]
        sim_config["n_timesteps"]
        sim_config["dt"]
        sim_config["start_time"]
        sim_config["timezone"]
        solar_resource_specs = self.options["resource_config"][
            "resource_parameters"
        ]  # TODO: update based on handling in H2IModel
        solar_resource_specs.setdefault("latitude", site_config["latitude"])
        solar_resource_specs.setdefault("longitude", site_config["longitude"])

        solar_resource_specs.setdefault(
            "resource_dir", site_config["resources"].get("resource_dir", "")
        )

        self.config = SolarResourceBaseAPIConfig.from_dict(solar_resource_specs)

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pass
