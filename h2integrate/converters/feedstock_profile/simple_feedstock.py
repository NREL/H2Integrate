import pandas as pd
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains


@define
class BasicFeedstockPerformanceModelConfig(BaseConfig):
    """
    Configuration class for the BasicFeedstockPerformanceModel.

    Args:
        commodity (str): The name of the commodity
        compute_mode (str): The compute mode
        profile (str): The relative path to the supply profile
        unit (str): The units that the supply profile is in
    """

    commodity: str = field()
    compute_mode: str = field(validator=contains(["normal", "feedstock_size", "product_size"]))
    profile: str = field()
    unit: str = field()


class BasicFeedstockPerformanceModel(om.ExplicitComponent):
    """
    A simple OpenMDAO component that determines supply of a feedstock.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        super().setup()
        self.config = BasicFeedstockPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        if self.config.compute_mode == "product_size":
            self.add_input(
                self.config.commodity + "_demand", units=self.config.unit, shape_by_conn=True
            )
        self.add_output(self.config.commodity + "_out", units=self.config.unit, shape_by_conn=True)

    def compute(self, inputs, outputs):
        if self.config.compute_mode != "product_size":
            path = self.config.profile
            profile = pd.read_csv(path, header=None).values[:, 0]
        else:
            profile = inputs[self.config.commodity + "_demand"]
        outputs[self.config.commodity + "_out"] = profile


@define
class BasicFeedstockCostModelConfig(BaseConfig):
    """
    Configuration class for the BasicFeedstockCostModel.

    Args:
        commodity (str): The name of the commodity
        buy_price (float): The buying price of the commodity
    """

    commodity: str = field()
    buy_price: float = field()


class BasicFeedstockCostModel(om.ExplicitComponent):
    """
    An OpenMDAO component that computes the cost of a feedstock.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        super().setup()
        self.config = BasicFeedstockCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        self.add_input(self.config.commodity + "_out", shape_by_conn=True)
        self.add_output("CapEx", units="USD")
        self.add_output("OpEx", units="USD/year")

    def compute(self, inputs, outputs):
        outputs["CapEx"] = 0
        outputs["OpEx"] = inputs[self.config.commodity + "_out"] * self.config.buy_price
