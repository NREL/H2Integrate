# Utilizing Sizing Modes with Resizeable Converters

When the size of one converter is changed, it may be desirable to have other converters in the plant resized to match.
This can be done manually by setting the sizes of each converter in the  `tech_config`, but it can also be done automatically with resizeable converters.
Resizeable converters can execute their own built-in sizing methods based on how much of a feedstock can be produced upstream, or how much of a commodity can be offtaken downstream by other converters.
By connecting the capacities of converters to other converters, one can build a logical re-sizing scheme for a multi-technology plant that will resize all converters by changing just one config parameter.

## Setting up a resizeable converter

To set up a resizeable converter, take advantage of the `ResizeablePerformanceModelBaseConfig` and `ResizeablePerformanceModelBaseClass`.
The `ResizeablePerformanceModelBaseConfig` will declare a `sizing` performance parameter within the the tech_config, which is a dict that specifies the sizing mode.
The `ResizeablePerformanceModelBaseClass` will automatically parse this dict into the `inputs` and `discrete_inputs` that the performance model will need for resizing.
Here is the start of an example `tech_config` for such a converter:

```
tech_config = {
    "model_inputs": {
        "shared_parameters": {
            "production_capacity": 1000.0,
        },
        "performance_parameters": {
            "sizing": {
                "size_mode": "normal",  # Always required
                "resize_by_flow": "electricity",  # Not required in "normal" mode
                "max_feedstock_ratio": 1.6,  # Only used in "resize_by_max_feedstock"
                "max_commodity_ratio": 0.7,  # Only used in "resize_by_max_commodity"
            },
        },
    }
}
```

Currently, there are three different modes defined for `size_mode`:

- `normal`: In this mode, converters function as they always have previously:
    - The size of the asset is fixed within `compute()`.
- `resize_by_max_feedstock`: In this mode, the size of the converter is adjusted to be able to utilize all of the available feedstock:
    - The size of the asset should be calculated within `compute()` as a function of the maximum value of `<feedstock>_in` - with the `<feedstock>` specified by the `resize_by_flow` parameter.
    - This function will utilizes the `"max_feedstock_ratio"` parameter - e.g., if `"max_feedstock_ratio"` is 1.6, the converter will be resized so that its input capacity is 1.6 times the max of `<feedstock>_in`.
    - The `set_val` method will over-write any previous sizing varaibles to reflect the adjusted size of the converter.
- `resize_by_max_commodity`: In this mode, the size of the asset is adjusted to be able to supply its product to the full capacity of another downstream converter:
    - The size of the asset should be calculated within `compute()` as a function of the `max_<commodity>_capacity` input - with the `<feedstock>` specified by the `resize by flow` parameter.
    - This function will utilizes the `"max_commodity_ratio"` parameter - e.g., if `"max_commodity_ratio"` is 0.7, the converter will be resized so that its output capacity is 0.7 times a connected `"max_<commodity>_capacity"` input.
    - The `set_val` method will over-write any previous sizing varaibles to reflect the adjusted size of the converter.

To construct a resizeable converter from an existing converter, very few changes must be made, and only to the performance model.
`ResizeablePerformanceModelBaseConfig` can replace `BaseConfig` and `ResizeablePerformanceModelBaseClass` can replace `om.ExplicitComponent`.
The setup function must be modified to include any `"max_<feedstock>_capacity"` outputs or `"max_<commodity>_capacity"` inputs that can be connected to do the resizing.
Then, any `feedstock_sizing_function` or `feedstock_sizing_function` that the converter needs to resize itself should be defined, if not already.
Finally, the compute method should be modified (near the start, before any size-based calculations occur) to modify the size with these functions:

```
import numpy as np
from h2integrate.core.utilities import ResizeablePerformanceModelBaseConfig, merge_shared_inputs
from h2integrate.core.model_baseclasses import ResizeablePerformanceModelBaseClass


class TechPerformanceModelConfig(ResizeablePerformanceModelBaseConfig):
    # Declare tech-specific config parameters
    size: float = 1.0


class TechPerformanceModel(ResizeablePerformanceModelBaseClass):
    def setup(self):
        self.config = TechPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=False,
        )
        super().setup()

        # Declare tech-specific inputs and outputs
        self.add_input("size", val=self.config.size, units="unitless")
        # Declare any commodities produced that need to be connected to downstream converters
        # if this converter is in `resize_by_max_commodity` mode
        self.add_input("max_<commodity>_capacity", val=1000.0, units="kg/h")
        # Any feedstocks consumed that need to be connected to upstream converters
        # if those converters are in `resize_by_max_commodity` mode
        self.add_output("max_<feedstock>_capacity", val=1000.0, units="kg/h")

    def feedstock_sizing_function(max_feedstock):
        max_feedstock * 0.1231289  # random number for example

    def commodity_sizing_function(max_commodity):
        max_commodity * 0.4651  # random number for example

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        size_mode = discrete_inputs["size_mode"]

        # Make changes to computation based on sizing_mode:
        if size_mode != "normal":
            size = inputs["size"]
            if size_mode == "resize_by_max_feedstock":
                if inputs["resize_by_flow"] == "<feedstock>":
                    feed_ratio = inputs["max_feedstock_ratio"]
                    size_for_max_feed = self.feedstock_sizing_function(
                        np.max(inputs["<feedstock>_in"])
                    )
                    size = size_for_max_feed * feed_ratio
            elif size_mode == "resize_by_max_commodity":
                if inputs["resize_by_flow"] == "<commodity>":
                    comm_ratio = inputs["max_commodity_ratio"]
                    size_for_max_comm = self.commodity_sizing_function(
                        np.max(inputs["max_<commodity>_capacity"])
                    )
                    size = size_for_max_comm * comm_ratio
            self.set_val("size", size)
```

## Example plant setup

An example plant with resizeable technologies is set up in `examples/22_sizing_modes/`.
Follow the examples in `run_size_modes.ipynb` to see how they work.
Here, there are three technologies in the the `tech_config.yaml`:
1. A `hopp` plant producing electricity,
2. An `electrolyzer` producing hydrogen from that electricity, and
3. An `ammonia` plant producting ammonia from that hydrogen.

The electrolyzer and ammonia technologies are resizeable.
They are set up in `"normal"` mode in the `tech_config`.

```
technologies:
  hopp:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "normal"
  electrolyzer:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "normal"
  ammonia:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "normal"
```

The `technology_interconnections` in the `plant_config` is set up to send electricity from the wind plant to the electrolyzer, then hydrogen from the electrolyzer to the ammonia plant.
There is also an entry to send the `max_hydrogen_capacity` from the ammonia plant to the electrolyzer, which will be required only in the `resize_by_max_commodity` mode.
Note: this creates a feedback loop within the OpenMDAO problem, which requires an iterative solver.

```
technology_interconnections: [
    ['hopp', 'electrolyzer', 'electricity', 'cable']
    ['electrolyzer', 'ammonia', 'hydrogen', 'pipe']
    ['ammonia', 'electrolyzer', 'max_hydrogen_capacity']
]
```

### `resize_by_max_feedstock` mode

In this case, the electrolyzer will be sized to match the maximum `electricity_in` coming from HOPP.
This increases the electrolyzer size to 1080 MW, the closest multiple of 40 MW (the cluster size) matching the max HOPP power output of 1048 MW.

```
technologies:
  hopp:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "normal"
  electrolyzer:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "size_by_max_feedstock"
          resize_by_flow: "electricity"
          max_feedstock_ratio: 1.0
  ammonia:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "normal"
```

### `resize_by_max_product` mode

In this case, the electrolyzer will be sized to match the maximum hydrogen capacity of the ammonia plant.
This requires the `technology_interconnections` entry to send the `max_hydrogen_capacity` from the ammonia plant to the electrolyzer.
This decreases the electrolyzer size to 560 MW, the closest multiple of 40 MW (the cluster size) that will ensure an h2 produciton capacity that matches the ammonia plant's h2 intake at its max ammonia produciton capacity.

```
technologies:
  hopp:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "normal"
  electrolyzer:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "size_by_max_commodity"
          resize_by_flow: "hydrogen"
          max_commodity_ratio: 1.0
  ammonia:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "normal"
```

## Using optimizer with multiple connections

With both `electrolyzer` and `ammonia` in `size_by_max_feedstock` mode, the COBYLA optimizer can co-optimize their `max_feedstock_ratio` variables to minimize the LCOA. This is achieved at a capacity factor of approximately 55% in both the electrolyzer and the ammonia plant.

In the `tech_config`:
```
technologies:
  hopp:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "normal"
  electrolyzer:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "size_by_max_feedstock"
          resize_by_flow: "electricity"
          max_feedstock_ratio: 1.0
  ammonia:
    model_inputs:
      performance_parameters:
        sizing:
          size_mode: "size_by_max_feedstock"
          resize_by_flow: "hydrogen"
          max_feedstock_ratio: 1.0
```
And in the `driver_config`:
```
driver:
  optimization:
    flag: True
    solver: COBYLA
    tol: 0.01
    catol: 15000
    max_iter: 100
    rhobeg: 0.1
    debug_print: True

design_variables:
  electrolyzer:
    max_feedstock_ratio:
      flag: True
      lower: 0.1
      upper: 10.
      units: unitless
  ammonia:
    max_feedstock_ratio:
      flag: True
      lower: 0.1
      upper: 10.
      units: unitless

objective:
  name: finance_subgroup_nh3.LCOA
```
End output from COBYLA:
```
Driver debug print for iter coord: rank0:ScipyOptimize_COBYLA|15
----------------------------------------------------------------
Design Vars
{'ammonia.max_feedstock_ratio': array([1.00961083]),
 'electrolyzer.max_feedstock_ratio': array([0.79723742])}

Nonlinear constraints
None

Linear constraints
None

Objectives
{'finance_subgroup_nh3.LCOA': array([1.19535981])}

Optimization Complete
-----------------------------------
```
