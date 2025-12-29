from pathlib import Path

import dill
import openmdao.api as om

from h2integrate.core.utilities import make_cache_hash_filename


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

    These parameters are all set as attributes within the config class, which inherits from
    h2integrate.core.utilities.ResizeablePerformanceModelBaseConfig

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


class CacheModelBaseClass(om.ExplicitComponent):
    """Baseclass to be used for any model that may cache results."""

    def load_outputs(self, inputs, outputs, discrete_inputs={}, config_dict: dict = {}):
        """Create filename for cached results using data from inputs and discrete_inputs.
        If the filepathe exists for the cached results, then sets the outputs values to the
        values in the cached results file and returns True. Otherwise, returns False.

        Args:
            inputs (om.vectors.default_vector.DefaultVector): OM inputs to `compute()` method
            outputs (om.vectors.default_vector.DefaultVector): OM outputs of `compute()` method
            discrete_inputs (om.core.component._DictValues, optional): OM discrete inputs to
                `compute()` method. Defaults to {}.
            config_dict (dict, optional): dictionary created/updated from config class.
                Defaults to {}. If config_dict is input as an empty dictionary,
                config_dict is created from `self.config.as_dict()`

        Returns:
            bool: True if outputs were set to cached results. False if cache file
                doesnt't exist and the model still needs to calculate and set the outputs.
        """
        if self.config.enable_caching:
            # check if config_dict was input
            if not bool(config_dict):
                # create config_dict from config attribute
                config_dict = self.config.as_dict()

            # create unique filename for cached results based on inputs and config
            cache_filename = make_cache_hash_filename(
                config_dict, inputs, discrete_inputs, cache_dir=self.config.cache_dir
            )

            # Check if file exists that contains cached results
            if not cache_filename.exists():
                # If file doesn't exist, return False to indicate that outputs have not been set
                return False

            # Load the cached results
            cache_path = Path(cache_filename)
            with cache_path.open("rb") as f:
                cached_data = dill.load(f)

            # Set outputs to the outputs saved in the cached results
            for output_name, default_output_val in outputs.items():
                outputs[output_name] = cached_data.get(output_name, default_output_val)
            # Return True to indicate that outputs have been set from cached results
            return True

    def cache_outputs(self, inputs, outputs, discrete_inputs={}, config_dict: dict = {}):
        """Create filename for cached results using data from inputs and discrete_inputs.
        Save dictionary of outputs to the file.

        Args:
            inputs (om.vectors.default_vector.DefaultVector): OM inputs to `compute()` method
            outputs (om.vectors.default_vector.DefaultVector): OM outputs of `compute()` method
                that have already been set with the resulting values
            discrete_inputs (om.core.component._DictValues, optional): OM discrete inputs to
                `compute()` method. Defaults to {}.
            config_dict (dict, optional): dictionary created/updated from config class.
                Defaults to {}. If config_dict is input as an empty dictionary,
                config_dict is created from `self.config.as_dict()`
        """
        # Cache the results for future use
        if self.config.enable_caching:
            # check if config_dict was input
            if not bool(config_dict):
                # create config_dict from config attribute
                config_dict = self.config.as_dict()

            # create unique filename for cached results based on inputs and config
            cache_filename = make_cache_hash_filename(
                config_dict, inputs, discrete_inputs, cache_dir=self.config.cache_dir
            )

            cache_path = Path(cache_filename)

            # Save outputs to pickle file
            with cache_path.open("wb") as f:
                output_dict = dict(outputs.items())
                dill.dump(output_dict, f)

    # def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
    #     """
    #     Computation for the OM component.
    #     This template includes commented out code on how to use the functionality
    #     of this component within a model.

    #     For a template class this is not implement and raises an error.
    #         """

    #     # 1. check if this case has been run before
    #     loaded_results = self.load_outputs(inputs, outputs, discrete_inputs)
    #     if loaded_results:
    #         return

    #     # 2. run model as normal and set outputs

    #     # 3. save outputs to cache directory
    #     self.cache_outputs(inputs, outputs, discrete_inputs)

    #     raise NotImplementedError("This method should be implemented in a subclass.")
