import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs


@define
class SimpleGenericStorageConfig(BaseConfig):
    resource_name: str = field()
    resource_rate_units: str = field()


class SimpleGenericStorage(om.ExplicitComponent):
    """
    Simple generic storage model.
    """

    def initialize(self):
        self.options.declare("tech_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("driver_config", types=dict)

    def setup(self):
        super().setup()
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        self.config = SimpleGenericStorageConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=False,
        )
        resource_name = self.config.resource_name
        resource_rate_units = self.config.resource_rate_units
        self.add_input(f"{resource_name}_in", val=0.0, shape=n_timesteps, units=resource_rate_units)

    def compute(self, inputs, outputs):
        pass
