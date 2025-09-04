from typing import ClassVar

from attrs import field, define

from h2integrate.core.validators import range_val
from h2integrate.resource.resource_base import ResourceBaseAPIModel, ResourceBaseAPIConfig


@define
class WTKNRELDeveloperAPIConfig(ResourceBaseAPIConfig):
    resource_year: int = field(converter=int, validator=range_val(2007, 2014))
    dataset_desc: str = "wtk_v2"
    resource_type: str = "wind"
    valid_intervals: ClassVar = [5, 15, 30, 60]


class WTKNRELDeveloperAPIModel(ResourceBaseAPIModel):
    def setup(self):
        # initialize inputs for config
        site_config = self.site_config = self.options["plant_config"]["site"]
        sim_config = self.options["plant_config"]["plant"]["simulation"]
        resource_specs = self.options["resource_config"][
            "resource_parameters"
        ]  # TODO: update based on handling in H2IModel
        resource_specs.setdefault("latitude", site_config["latitude"])
        resource_specs.setdefault("longitude", site_config["longitude"])
        resource_specs.setdefault(
            "resource_dir", site_config["resources"].get("resource_dir", None)
        )
        resource_specs.setdefault("timezone", sim_config.get("timezone"))
        self.config = WTKNRELDeveloperAPIConfig.from_dict(resource_specs)

        # check what steps to do
        # 1) check if user provided data
        # if bool(self.config.data):
