import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class SplitterPerformanceConfig(BaseConfig):
    split_mode: str = field()
    split_ratio: float = field()
    prescribed_electricity: float = field()


class SplitterPerformanceModel(om.ExplicitComponent):
    """
    Split power from one source into two outputs.

    This component supports two splitting modes:
    1. Ratio-based splitting: Split based on a specified ratio
    2. Prescribed electricity splitting: Send a prescribed amount to output1, remainder to output2

    This component is purposefully simple; a more realistic case might include
    losses or other considerations from power electronics.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict, default={})
        self.options.declare("plant_config", types=dict, default={})
        self.options.declare("tech_config", types=dict, default={})

    def setup(self):
        # Initialize config from tech_config
        self.config = SplitterPerformanceConfig.from_dict(
            self.options["tech_config"].get("performance_model", {}).get("config", {})
        )

        self.add_input("electricity_in", val=0.0, shape_by_conn=True, units="kW")

        split_mode = self.config.split_mode

        if split_mode == "ratio":
            self.add_input(
                "split_ratio",
                val=self.config.split_ratio,
                desc="Fraction of input power to send to output1 (0.0 to 1.0)",
            )
        elif split_mode == "prescribed_electricity":
            self.add_input(
                "prescribed_electricity",
                val=self.config.prescribed_electricity,
                copy_shape="electricity_in",
                units="kW",
                desc="Prescribed amount of power to send to output1",
            )
        else:
            raise ValueError(
                f"Invalid split_mode: {split_mode}. Must be 'ratio' or 'prescribed_electricity'"
            )

        self.add_output("electricity_out1", val=0.0, copy_shape="electricity_in", units="kW")
        self.add_output("electricity_out2", val=0.0, copy_shape="electricity_in", units="kW")

    def compute(self, inputs, outputs):
        electricity_in = inputs["electricity_in"]
        split_mode = self.config.split_mode

        if split_mode == "ratio":
            split_ratio = inputs["split_ratio"]
            # Ensure ratio is between 0 and 1
            split_ratio = np.clip(split_ratio, 0.0, 1.0)
            outputs["electricity_out1"] = electricity_in * split_ratio
            outputs["electricity_out2"] = electricity_in * (1.0 - split_ratio)

        elif split_mode == "prescribed_electricity":
            prescribed_electricity = inputs["prescribed_electricity"]
            # Ensure prescribed electricity is non-negative and doesn't exceed available power
            available_power = np.maximum(0.0, electricity_in)
            requested_amount = np.maximum(0.0, prescribed_electricity)
            actual_amount = np.minimum(requested_amount, available_power)

            outputs["electricity_out1"] = actual_amount
            outputs["electricity_out2"] = electricity_in - actual_amount
