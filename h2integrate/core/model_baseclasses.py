import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define(kw_only=True)
class CostModelBaseConfig(BaseConfig):
    cost_year: int = field(converter=int)


class CostModelBaseClass(om.ExplicitComponent):
    """Baseclass to be used for all cost models. The built-in outputs
    are used by the finance model and must be outputted by all cost models.

    It is suggested to use CostModelBaseConfig as the base class for
    configuration classes that are used in subclasses that inherit this class.

    Outputs:
        - CapEx (float): capital expenditure costs in $
        - OpEx (float): annual fixed operating expenditure costs in $/year
        - VarOpEx (float): annual variable operating expenditure costs in $/year

    Discrete Outputs:
        - cost_year (int): dollar-year corresponding to CapEx and OpEx values.
            This may be inherent to the cost model, or may depend on user provided input values.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        plant_life = int(self.options["plant_config"]["plant"]["plant_life"])
        # Define outputs: CapEx and OpEx costs
        self.add_output("CapEx", val=0.0, units="USD", desc="Capital expenditure")
        self.add_output("OpEx", val=0.0, units="USD/year", desc="Fixed operational expenditure")
        self.add_output(
            "VarOpEx",
            val=0.0,
            shape=plant_life,
            units="USD/year",
            desc="Variable operational expenditure",
        )
        # Define discrete outputs: cost_year
        self.add_discrete_output(
            "cost_year", val=self.config.cost_year, desc="Dollar year for costs"
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")


@define(kw_only=True)
class ResizeablePerformanceModelBaseConfig(BaseConfig):
    size_mode: str = field(default="normal")
    flow_used_for_sizing: str | None = field(default=None)
    max_feedstock_ratio: float = field(default=1.0)
    max_commodity_ratio: float = field(default=1.0)

    def __attrs_post_init__(self):
        """Validate sizing parameters after initialization."""
        valid_modes = ["normal", "resize_by_max_feedstock", "resize_by_max_commodity"]
        if self.size_mode not in valid_modes:
            raise ValueError(
                f"Sizing mode '{self.size_mode}' is not a valid sizing mode. "
                f"Options are {valid_modes}."
            )

        if self.size_mode != "normal":
            if self.flow_used_for_sizing is None:
                raise ValueError(
                    "'flow_used_for_sizing' must be set when size_mode is "
                    "'resize_by_max_feedstock' or 'resize_by_max_commodity'"
                )


class ResizeablePerformanceModelBaseClass(om.ExplicitComponent):
    """Baseclass to be used for all resizeable performance models. The built-in inputs
    are used by the performance models to resize themselves.

    These parameters are all set as attributes within the config class, which inherits from
    ResizeablePerformanceModelBaseConfig

    Discrete Inputs:
        - size_mode (str): The mode in which the component is sized. Options:
            - "normal": The component size is taken from the tech_config.
            - "resize_by_max_feedstock": The component size is calculated relative to the
                maximum available amount of a certain feedstock or feedstocks
            - "resize_by_max_commodity": The electrolyzer size is calculated relative to the
                maximum amount of the commodity used by another tech
        - flow_used_for_sizing (str): The feedstock/commodity flow used to determine the plant size
            in "resize_by_max_feedstock" and "resize_by_max_commodity" modes

    Inputs:
        - max_feedstock_ratio (float): The ratio of the max feedstock that can be consumed by
            this component to the max feedstock available.
        - max_commodity_ratio (float): The ratio of the max commodity that can be produced by
            this component to the max commodity consumed by the downstream tech.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        # Parse in sizing parameters
        size_mode = self.config.size_mode
        self.add_discrete_input("size_mode", val=size_mode)

        if size_mode not in ["normal", "resize_by_max_feedstock", "resize_by_max_commodity"]:
            raise ValueError(
                f"Sizing mode '{size_mode}' is not a valid sizing mode."
                " Options are 'normal', 'resize_by_max_feedstock',"
                "'resize_by_max_commodity'."
            )

        if size_mode != "normal":
            if self.config.flow_used_for_sizing is not None:
                size_flow = self.config.flow_used_for_sizing
                self.add_discrete_input("flow_used_for_sizing", val=size_flow)
            else:
                raise ValueError(
                    "'flow_used_for_sizing' must be set when size_mode is "
                    "'resize_by_max_feedstock' or 'resize_by_max_commodity'"
                )
            if size_mode == "resize_by_max_commodity":
                comm_ratio = self.config.max_commodity_ratio
                self.add_input("max_commodity_ratio", val=comm_ratio, units="unitless")
            else:
                feed_ratio = self.config.max_feedstock_ratio
                self.add_input("max_feedstock_ratio", val=feed_ratio, units="unitless")

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")
