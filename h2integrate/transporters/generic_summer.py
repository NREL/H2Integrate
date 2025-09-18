import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs


@define
class GenericProductionSummerPerformanceConfig(BaseConfig):
    """Configuration class for a generic summer for commodities.

    Attributes:
        commodity (str): name of commodity type
        commodity_units (str): units of commodity production profile
    """

    commodity: str = field(converter=(str.lower, str.strip))
    commodity_units: str = field()


class GenericProductionSummerPerformanceModel(om.ExplicitComponent):
    """
    Sum the production profile of some commodity from a single source.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = GenericProductionSummerPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])

        if self.config.commodity == "electricity":
            # NOTE: this should be updated in overhaul required for flexible dt
            summed_units = f"{self.config.commodity_units}*h"
        else:
            summed_units = self.config.commodity_units

        self.add_input(
            f"{self.config.commodity}_in",
            val=0.0,
            shape=n_timesteps,
            units=self.config.commodity_units,
        )
        self.add_output(f"total_{self.config.commodity}_produced", val=0.0, units=summed_units)

    def compute(self, inputs, outputs):
        outputs[f"total_{self.config.commodity}_produced"] = sum(
            inputs[f"{self.config.commodity}_in"]
        )


@define
class GenericConsumptionSummerPerformanceConfig(BaseConfig):
    """Configuration class for a generic summer for feedstocks.

    Attributes:
        feedstock (str): name of feedstock type
        feedstock_units (str): units of feedstock consumption profile
    """

    feedstock: str = field(converter=(str.lower, str.strip))
    feedstock_units: str = field()


class GenericConsumptionSummerPerformanceModel(om.ExplicitComponent):
    """
    Sum the consumption profile of some feedstock from a single source.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = GenericConsumptionSummerPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])

        if self.config.feedstock == "electricity":
            # NOTE: this should be updated in overhaul required for flexible dt
            summed_units = f"{self.config.feedstock}*h"
        else:
            summed_units = self.config.feedstock

        self.add_input(
            f"{self.config.feedstock}_in",
            val=0.0,
            shape=n_timesteps,
            units=self.config.feedstock_units,
        )
        self.add_output(f"total_{self.config.feedstock}_consumed", val=0.0, units=summed_units)

    def compute(self, inputs, outputs):
        outputs[f"total_{self.config.feedstock}_consumed"] = sum(
            inputs[f"{self.config.feedstock}_in"]
        )
