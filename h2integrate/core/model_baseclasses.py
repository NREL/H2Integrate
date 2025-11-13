import openmdao.api as om


class CostModelBaseClass(om.ExplicitComponent):
    """Baseclass to be used for all cost models. The built-in outputs
    are used by the finance model and must be outputted by all cost models.

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


class ResizeablePerformanceModelBaseClass(om.ExplicitComponent):
    """Baseclass to be used for all resizeable performance models. The built-in inputs
    are used by the performance models to resize themselves.

    Discrete Inputs:
        - size_mode (str): The mode in which the component is sized. Options:
            - "normal": The component size is taken from the tech_config.
            - "resize_by_max_feedstock": The component size is calculated relative to the
                maximum available amount of a certain feedstock or feedstocks
            - "resize_by_max_commodity": The electrolyzer size is calculated relative to the
                maximum amount of the commodity used by another tech
        - resize_by_flow (str): The feedstock/commodity flow used to determine the plant size
            in "resize_by_max_feedstock" and "resize_by_max_commodity" modes
        - resize_by_tech (str): A connected tech whose feedstock/commodity flow is used to
            determine the plant size in "resize_for_max_product" mode

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
        size_mode = self.config.sizing["size_mode"]
        self.add_discrete_input("size_mode", val=size_mode)
        if size_mode != "normal":
            if "resize_by_flow" in self.config.sizing.keys():
                size_flow = self.config.sizing["resize_by_flow"]
                self.add_discrete_input("resize_by_flow", val=size_flow)
            else:
                raise ValueError(
                    "'resize_by_flow' must be set in sizing dict when size_mode is "
                    "'resize_by_max_feedstock' or 'resize_by_max_commodity'"
                )
            if size_mode == "resize_by_max_commodity":
                if "resize_by_tech" in self.config.sizing.keys():
                    size_tech = self.config.sizing["resize_by_tech"]
                    self.add_discrete_input("resize_by_tech", val=size_tech)
                    if "max_commodity_ratio" in self.config.sizing.keys():
                        comm_ratio = self.config.sizing["max_commodity_ratio"]
                    else:
                        comm_ratio = 1.0
                    self.add_input("max_commodity_ratio", val=comm_ratio, units="unitless")
                else:
                    raise ValueError(
                        "'resize_by_tech' must be set in sizing dict when size_mode is "
                        "'resize_by_max_commodity'"
                    )
            else:
                if "max_feedstock_ratio" in self.config.sizing.keys():
                    feed_ratio = self.config.sizing["max_feedstock_ratio"]
                else:
                    feed_ratio = 1.0
                self.add_input("max_feedstock_ratio", val=feed_ratio, units="unitless")
        elif size_mode != "normal":
            raise ValueError("Sizing mode '%s' is not a valid sizing mode".format())

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")
