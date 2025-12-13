import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs


@define(kw_only=True)
class GenericCombinerPerformanceConfig(BaseConfig):
    """Configuration class for a generic combiner.

    Attributes:
        commodity (str): name of commodity type
        commodity_units (str): units of commodity production profile
    """

    commodity: str = field(converter=(str.lower, str.strip))
    commodity_units: str = field()


class GenericCombinerPerformanceModel(om.ExplicitComponent):
    """
    Combine any commodity or resource from two sources into one output without losses.

    This component is purposefully simple; a more realistic case might include
    losses or other considerations from system components.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = GenericCombinerPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])

        self.add_input(
            f"{self.config.commodity}_in1",
            val=0.0,
            shape=n_timesteps,
            units=self.config.commodity_units,
        )
        self.add_input(
            f"{self.config.commodity}_in2",
            val=0.0,
            shape=n_timesteps,
            units=self.config.commodity_units,
        )
        self.add_output(
            f"{self.config.commodity}_out",
            val=0.0,
            shape=n_timesteps,
            units=self.config.commodity_units,
        )

    def compute(self, inputs, outputs):
        outputs[f"{self.config.commodity}_out"] = (
            inputs[f"{self.config.commodity}_in1"] + inputs[f"{self.config.commodity}_in2"]
        )
