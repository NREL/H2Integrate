import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class SplitterPerformanceConfig(BaseConfig):
    split_mode: str = field()
    fraction_of_electricity_to_first_tech: float = field(default=None)
    prescribed_electricity_to_first_tech: float = field(default=None)

    def __attrs_post_init__(self):
        """Validate that the required fields are present based on split_mode."""
        if self.split_mode == "fraction":
            if self.fraction_of_electricity_to_first_tech is None:
                raise ValueError(
                    "fraction_of_electricity_to_first_tech is required"
                    " when split_mode is 'fraction'"
                )
        elif self.split_mode == "prescribed_electricity":
            if self.prescribed_electricity_to_first_tech is None:
                raise ValueError(
                    "prescribed_electricity_to_first_tech is required"
                    " when split_mode is 'prescribed_electricity'"
                )
        else:
            raise ValueError(
                f"Invalid split_mode: {self.split_mode}."
                " Must be 'fraction' or 'prescribed_electricity'"
            )

        # Set default values for unused fields
        if self.split_mode == "fraction" and self.prescribed_electricity_to_first_tech is None:
            self.prescribed_electricity_to_first_tech = 0.0
        elif (
            self.split_mode == "prescribed_electricity"
            and self.fraction_of_electricity_to_first_tech is None
        ):
            self.fraction_of_electricity_to_first_tech = 0.0


class SplitterPerformanceModel(om.ExplicitComponent):
    """
    Split power from one source into two outputs.

    This component supports two splitting modes:
    1. Fraction-based splitting: Split based on a specified fraction sent to the first technology
    2. Prescribed electricity splitting: Send a prescribed amount to the first technology,
       remainder to the second

    The outputs are:
    - electricity_out1: Power sent to the first technology
    - electricity_out2: Power sent to the second technology (remainder)

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

        if split_mode == "fraction":
            self.add_input(
                "fraction_of_electricity_to_first_tech",
                val=self.config.fraction_of_electricity_to_first_tech,
                desc="Fraction of input power to send to the first technology (0.0 to 1.0)",
            )
        elif split_mode == "prescribed_electricity":
            self.add_input(
                "prescribed_electricity_to_first_tech",
                val=self.config.prescribed_electricity_to_first_tech,
                copy_shape="electricity_in",
                units="kW",
                desc="Prescribed amount of power to send to the first technology",
            )
        else:
            raise ValueError(
                f"Invalid split_mode: {split_mode}. Must be 'fraction' or 'prescribed_electricity'"
            )

        self.add_output(
            "electricity_out1",
            val=0.0,
            copy_shape="electricity_in",
            units="kW",
            desc="Power output to the first technology",
        )
        self.add_output(
            "electricity_out2",
            val=0.0,
            copy_shape="electricity_in",
            units="kW",
            desc="Power output to the second technology (remainder)",
        )

    def compute(self, inputs, outputs):
        electricity_in = inputs["electricity_in"]
        split_mode = self.config.split_mode

        if split_mode == "fraction":
            fraction_to_first = inputs["fraction_of_electricity_to_first_tech"]
            # Ensure fraction is between 0 and 1
            fraction_to_first = np.clip(fraction_to_first, 0.0, 1.0)
            outputs["electricity_out1"] = electricity_in * fraction_to_first
            outputs["electricity_out2"] = electricity_in * (1.0 - fraction_to_first)

        elif split_mode == "prescribed_electricity":
            prescribed_to_first = inputs["prescribed_electricity_to_first_tech"]
            # Ensure prescribed electricity is non-negative and doesn't exceed available power
            available_power = np.maximum(0.0, electricity_in)
            requested_amount = np.maximum(0.0, prescribed_to_first)
            actual_amount = np.minimum(requested_amount, available_power)

            outputs["electricity_out1"] = actual_amount
            outputs["electricity_out2"] = electricity_in - actual_amount
