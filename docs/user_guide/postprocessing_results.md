# Postprocessing results

When running H2Integrate, results from the simulation and individual technologies are generated automatically.
Additionally, the raw numerical results are available in the resulting Python object `prob` after a simulation.
This doc page will walk you through the steps to postprocess the results from a simulation.

```{note}
Streamlining the postprocessing of results is an ongoing effort in H2Integrate -- please expect this page to be updated as new features are added.
```

## Automatically generated results

At the conclusion of a simulation, H2Integrate automatically prints a list of all the inputs and outputs for the model to the terminal.
Here is a snippet of the output from a simulation:

```text
37 Explicit Output(s) in 'model'

varname                               val                  units     prom_name
------------------------------------  -------------------  --------  -----------------------------------------------
plant
  hopp
    hopp
      electricity                     |85854400.89803042|  kW        hopp.electricity
      CapEx                           [4.00631628e+09]     USD       hopp.CapEx
      OpEx                            [70417369.71000001]  USD/year  hopp.OpEx
  hopp_to_steel_cable
    electricity_output                |85854400.89803042|  kW        hopp_to_steel_cable.electricity_output
  hopp_to_electrolyzer_cable
    electricity_output                |85854400.89803042|  kW        hopp_to_electrolyzer_cable.electricity_output
  electrolyzer
    eco_pem_electrolyzer_performance
      hydrogen                        |1514447.39634248|   kg/h      electrolyzer.hydrogen
      time_until_replacement          [43961.84207719]     h         electrolyzer.time_until_replacement
      total_hydrogen_produced         [1.18206537e+08]     kg/year   electrolyzer.total_hydrogen_produced
      efficiency                      [0.7206635]          None      electrolyzer.efficiency
    eco_pem_electrolyzer_cost
      CapEx                           [1.63021997e+09]     USD       electrolyzer.CapEx
      OpEx                            [39921515.0500124]   USD/year  electrolyzer.OpEx
```

Anywhere that the value is listed as a magnitude (e.g. `|85854400.89803042|`), this indicates that the value reported is the magnitude of the array.
Other values are reported as arrays (e.g. `[4.00631628e+09]`), which indicates that the value is a single element.
The units of the value are also reported, as well as the name of the variable in the model.
The name of the variable in the model is the last column in the table, and is used to access the value in the `prob` object.

```{note}
If the technologies you're modeling have been set up to generate results, the results will be printed or saved at this time as well.
```

## Manually postprocessing results

Once the simulation is complete, the results are available in the `prob` object.
This object is a dictionary-like object that contains all the inputs and outputs for the model.
The keys in the object are the names of the variables in the model, and the values are the values of the variables.

Here is an example of how to access the results from the `prob` object:

```python
from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a H2Integrate model
model = H2IntegrateModel("top_level_config.yaml")

# Run the model
model.run()

model.post_process()

print(model.prob.get_val("electrolyzer.total_hydrogen_produced", units='kg'))
```

This will print the total hydrogen produced by the electrolyzer in kg.
The `get_val` method is used to access the value of the variable in the `prob` object.
The `units` argument is used to specify the units of the value to be returned.
