import numpy as np
import pandas as pd
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains


@define
class BasicProductPerformanceModelConfig(BaseConfig):
    """
    Configuration class for the BasicProductPerformanceModel.

    Args:
        commodity (str): The name of the commodity
        compute_mode (str): The compute mode
        profile (str): The relative path to the demand profile
        unit (str): The units that the demand profile is in
    """

    commodity: str = field()
    compute_mode: str = field(validator=contains(["normal", "feedstock_size", "product_size"]))
    profile: str = field()
    unit: str = field()


class BasicProductPerformanceModel(om.ExplicitComponent):
    """
    A simple OpenMDAO component that determines demand of a product.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        super().setup()
        self.config = BasicProductPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        if self.config.compute_mode == "product_size":
            profile_name = self.config.commodity + "_profile"
            path = self.config.profile
            profile = pd.read_csv(path, header=None).values[:, 0]
            self.add_input(profile_name, units=self.config.unit, val=profile)
        else:
            profile_name = self.config.commodity + "_in"
            self.add_input(profile_name, units=self.config.unit, shape_by_conn=True)
        self.add_output(
            self.config.commodity + "_consume",
            units=self.config.unit,
            shape_by_conn=True,
            copy_shape=profile_name,
        )

    def compute(self, inputs, outputs):
        if self.config.compute_mode == "product_size":
            profile_name = self.config.commodity + "_profile"
        else:
            profile_name = self.config.commodity + "_in"
        profile = inputs[profile_name]
        outputs[self.config.commodity + "_consume"] = profile


@define
class BasicProductCostModelConfig(BaseConfig):
    """
    Configuration class for the BasicProductCostModel.

    Args:
        commodity (str): The name of the commodity
        sell_price (float): The selling price of the commodity
        is_coproduct (bool): Whether or not the commodity is a co-product that can be sold
        unit (str): The units that the demand profile is in
    """

    commodity: str = field()
    sell_price: float = field()
    is_coproduct: bool = field()
    unit: str = field()


class BasicProductCostModel(om.ExplicitComponent):
    """
    An OpenMDAO component that computes the sales of a co-product.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        super().setup()
        self.config = BasicProductCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        self.add_input(
            self.config.commodity + "_consume", shape_by_conn=True, units=self.config.unit
        )
        self.add_output("CapEx", units="USD")
        self.add_output("OpEx", units="USD/year")

    def compute(self, inputs, outputs):
        outputs["CapEx"] = 0
        if self.config.is_coproduct:
            outputs["OpEx"] = (
                np.sum(inputs[self.config.commodity + "_consume"]) * self.config.buy_price
            )
        else:
            outputs["OpEx"] = 0
