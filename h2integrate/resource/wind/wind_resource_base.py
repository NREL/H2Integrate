from attrs import define

from h2integrate.resource.resource_base import ResourceBaseAPIModel, ResourceBaseAPIConfig


@define
class WindResourceBaseAPIConfig(ResourceBaseAPIConfig):
    resource_type: str = "wind"


class WindResourceBaseAPIModel(ResourceBaseAPIModel):
    def setup(self):
        super().setup()
        self.add_input("hub_height", val=0.0, units="m")
        self.add_output("windspeed_", val=0.0, shape=self.n_timesteps, units="m/s")
        self.add_output("winddirection_", val=0.0, shape=self.n_timesteps, units="?")
