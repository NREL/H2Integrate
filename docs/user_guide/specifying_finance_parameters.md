# Finance Parameters

The finance model, finance model specific inputs, and cost adjustment information (regardless of the finance model) are required in the `finance_parameters` of the `plant_config`.

```{note}
The `plant_life` parameter from the `plant` section of the `plant_config` is also used in finance calculations as the operating life of the plant.
```

The `finance_parameters` section always requires the following information:
- `cost_adjustment_parameters`:
  - `target_dollar_year`: dollar-year to convert costs to.
  - `cost_year_adjustment_inflation` is used to adjust costs for each technology from the cost year of the technology model (see [details on cost years and cost models here](cost:cost_years) to the `target_dollar_year`

Other common variables to include in the `finance_parameters` section are:
- **finance_model** (string): Name of the general financial model to use. This should not be a technology specific finance model.
- **model_inputs** (dictionary): Input parameters for `finance_model`
- **commodity** (str): The commodity used for calculations in the `finance_model`. This is input into general finance models as the `commodity_type` (see [here](finance:overview) for details on general finance models input).
- **commodity_desc** (str): Optional additional description of the commodity. This is input into the general finance model as the `description` if a single finance model is used for a subgroup (see [here](finance:overview) for details on general finance models inputs). This is not used if subgroups are not specified.

These variables may be included in `finance_parameters` in different formats depending on the use-case. The different formatting options are:
- [Without subgroups](finparam:nosubgroups)
- [Single finance model with subgroups](finparams:singlemodelsubgroups)
- [Nicknamed single finance model with subgroups](finparams:namedsinglemodelsubgroups)
- [Multiple finance models with subgroups](finparams:multimodelsubgroups)


(finparam:nosubgroups)=
## Not specifying subgroups
If no `subgroups` are specified, the user is limited to a single general finance model and a single commodity. The finance model will include costs from all the technologies included in the `tech_config` file.

General format:
```yaml
finance_parameters:
  commodity: "commodity_a"
  finance_model: "finance_model_a" #ex: "ProFastComp"
  model_inputs: #dictionary of inputs for finance_model_a
```

- Format explained:
  - **commodity_a**: a commodity produced by at least one technology in `tech_config`. Ex: "hydrogen".
  - **finance_model_a**: a general finance model. Ex: "ProFastComp".
- output naming convention:
  - `financials_subgroup_default.<finance_model_a_output>` where `<finance_model_a_output>` is an output from `finance_model_a` whose name includes the output parameter and some representation of the commodity (`commodity_a` in this example).
- examples that use this format:
  - [Example 7](https://github.com/NREL/H2Integrate/blob/develop/examples/07_run_of_river_plant/plant_config.yaml)


(finparams:singlemodelsubgroups)=
## Single financial model with subgroups
This format assumes that all subgroups use the same finance model. The `finance_groups` parameter for the `subgroups` is not required.

General format:
```yaml
finance_parameters:
  finance_model: "finance_model_a" #ex: "ProFastComp"
  model_inputs: #dictionary of inputs for finance_model_a
  subgroups:
    subgroup_a:
      commodity: "commodity_a" #required
      commodity_desc: "" #optional description of commodity_a
      technologies: ["tech_a"]
    subgroup_b:
      commodity: "commodity_b" #required
      commodity_desc: "" #optional description of commodity_b
      technologies: ["tech_a","tech_b"]
```

- Format explained:
  - **finance_model_a**: a general finance model. Ex: "ProFastComp".
  - **subgroup_a**:
    - **commodity_a**: commodity produced by `tech_a` to use in the financial calculation done in `finance_model_a`.
    - **tech_a**: a technology key in `tech_config['technologies']`, these costs are included in the financial calculation done in `finance_model_a`.
  - **subgroup_b**:
    - **commodity_b**: commodity produced by either `tech_a` and/or `tech_b` to use in the financial calculation done in `finance_model_a`.
    - **tech_a** and **tech_b**: technology keys in `tech_config['technologies']`, the costs of these technologies are included in the financial calculation done in `finance_model_a`.

- output naming convention:
  - `financials_subgroup_<subgroup_a>.<finance_model_a_output>`
    - `<finance_model_a_output>` is an output from `finance_model_a` whose name includes the output parameter and some representation of the **commodity** (`commodity_a` in this example) and the **commodity_desc** for **subgroup_a**. (which is an empty string in this example).
  - `financials_subgroup_<subgroup_b>.<finance_model_a_output>`
    - `<finance_model_a_output>` is an output from `finance_model_a` whose name includes the output parameter and some representation of the **commodity** (`commodity_b` in this example) and the **commodity_desc** for **subgroup_b**. (which is an empty string in this example).
- examples that use this format:
  - [Example 02](https://github.com/NREL/H2Integrate/tree/develop/examples/02_texas_ammonia/plant_config.yaml)
  - [Example 03 - CO2H](https://github.com/NREL/H2Integrate/tree/develop/examples/03_methanol/co2_hydrogenation/plant_config_co2h.yaml)
  - [Example 09 - OAE](https://github.com/NREL/H2Integrate/tree/develop/examples/09_co2/ocean_alkalinity_enhancement/plant_config.yaml)
  - [Example 09 - DOC](https://github.com/NREL/H2Integrate/tree/develop/examples/09_co2/direct_ocean_capture/plant_config.yaml)
  - [Example 09 - OAE Financials](https://github.com/NREL/H2Integrate/tree/develop/examples/09_co2/ocean_alkalinity_enhancement_financials/plant_config_financials.yaml)
  <!-- - [Example 05](/examples/)
  - 11, 12, 13, 14, 15, 17 -->

(finparams:namedsinglemodelsubgroups)=
## Nicknamed financial model with subgroups
This is an alternative format to [above](finparams:singlemodelsubgroups) that highlights some logic for [specifying multiple finance models](finparams:multimodelsubgroups). In this case, the `finance_groups` parameter is required for each `subgroup`.

General format:
```yaml
finance_parameters:
  finance_model_nickname_a:
    finance_model: "finance_model_a" #ex: "ProFastComp"
    model_inputs: #dictionary of inputs for finance_model_a
  subgroups:
    subgroup_a:
      commodity: "commodity_a" #required
      commodity_desc: "" #optional description of commodity_a
      finance_groups: [finance_model_nickname_a] #required in this case
      technologies: ["tech_a"]
    subgroup_b:
      commodity: "commodity_b" #required
      commodity_desc: "" #optional description of commodity_b
      finance_groups: [finance_model_nickname_a] #required in this case
      technologies: ["tech_b","tech_c"]
```

- Format explained:
  - **finance_model_nickname_a**: the name used to reference a specific finance model and its corresponding inputs.
  - **finance_model_a**: a general finance model. Ex: "ProFastComp".
  - **subgroup_a**:
    - **commodity_a**: commodity produced by `tech_a` to use in the financial calculation done in `finance_model_a`.
    - **tech_a**: a technology key in `tech_config['technologies']`, these costs are included in the financial calculation done in `finance_model_a`.
    - **finance_model_nickname_a**: the nickname(s) of the finance model and corresponding inputs to use for **subgroup_a** finance calculations.
  - **subgroup_b**:
    - **commodity_b**: commodity produced by either `tech_a` and/or `tech_b` to use in the financial calculation done in `finance_model_a`.
    - **tech_a** and **tech_b**: technology keys in `tech_config['technologies']`, the costs of these technologies are included in the financial calculation done in `finance_model_a`.
    - **finance_model_nickname_a**: the nickname(s) of the finance model and corresponding inputs to use for **subgroup_b** finance calculations.
- output naming convention:
  - `financials_subgroup_<subgroup_a>.<finance_model_a_output>`
    - `<finance_model_a_output>` is an output from `finance_model_a` whose name includes the output parameter and some representation of the **commodity** (`commodity_a` in this example) and the **commodity_desc** for **subgroup_a**. (which is an empty string in this example).
  - `financials_subgroup_<subgroup_b>.<finance_model_a_output>`
    - `<finance_model_a_output>` is an output from `finance_model_a` whose name includes the output parameter and some representation of the **commodity** (`commodity_b` in this example) and the **commodity_desc** for **subgroup_b**. (which is an empty string in this example).
- examples that use this format:
  - [Example 01](https://github.com/NREL/H2Integrate/blob/develop/examples/01_onshore_steel_mn/plant_config.yaml)


(finparams:multimodelsubgroups)=
## Multiple financial models with subgroups
This format is used to specify multiple general finance models and/or multiple commodity types.

General format:
```yaml
finance_parameters:
  finance_model_nickname_a:
    finance_model: "finance_model_a" #ex: "ProFastComp"
    model_inputs: #dictionary of inputs for the finance_model_a
  finance_model_nickname_b:
    finance_model: "finance_model_a" #ex: "ProFastComp"
    model_inputs: #dictionary of inputs for finance_model_a, these may be different than the model inputs for `finance_model_nickname_a`
  finance_model_nickname_c:
    finance_model: "finance_model_c" #ex: "NPVFinancial"
    model_inputs: #dictionary of inputs for finance_model_c
  subgroups:
    subgroup_a:
      commodity: "commodity_a" #required
      commodity_desc: "desc_a" #optional description of commodity_a
      finance_groups: [finance_model_nickname_a]
      technologies: ["tech_a"]
    subgroup_b:
      commodity: "commodity_a" #required
      commodity_desc: "desc_b" #optional description of commodity_b
      finance_groups: [finance_model_nickname_a, finance_model_nickname_b]
      technologies: ["tech_b","tech_c"]
    subgroup_c:
      commodity: "commodity_b" #required
      commodity_desc: "" #optional description of commodity_b
      finance_groups: [finance_model_nickname_a, finance_model_nickname_c]
      technologies: ["tech_b","tech_c"]
```
- Format explained:
  - **finance_model_nickname_a**: the name used to reference a specific finance model (`finance_model_a` in this example) and its corresponding inputs.
  - **finance_model_nickname_b**: the name used to reference a specific finance model (`finance_model_a` in this example) and its corresponding inputs.
  - **finance_model_nickname_c**: the name used to reference a specific finance model (`finance_model_c` in this example) and its corresponding inputs.
  - **finance_model_a**: a general finance model. Ex: "ProFastComp".
  - **finance_model_c**: a general finance model. Ex: "ProFastComp".
  - **subgroup_a**:
    - **commodity_a**: commodity produced by `tech_a` to use in the financial calculation done in `finance_model_a`.
    - **tech_a**: a technology key in `tech_config['technologies']`, these costs are included in the financial calculation done in `finance_model_a` (defined by **finance_model_nickname_a**)
    - **desc_a**: some descriptor for the finance output parameters from the **subgroup_a** financial model(s)
    - **finance_model_nickname_a**: the nickname(s) of the finance model and corresponding inputs to use for **subgroup_a** finance calculations.
  - **subgroup_b**:
    - **commodity_b**: commodity produced by either `tech_a` and/or `tech_b` to use in the financial calculation done in `finance_model_a` (defined by **finance_model_nickname_a** and **finance_model_nickname_b**)
    - **tech_a** and **tech_b**: technology keys in `tech_config['technologies']`, the costs of these technologies are included in the financial calculation done in `finance_model_a`.
    - **desc_b**: some descriptor for the finance output parameters from the **subgroup_b** financial model(s)
    - **finance_model_nickname_a** and **finance_model_nickname_b**: the nickname(s) of the finance model and corresponding inputs to use for **subgroup_b** finance calculations.
  - **subgroup_c**:
    - **commodity_b**: commodity produced by either `tech_b` and/or `tech_c` to use in the financial calculations done in `finance_model_a` (defined by **finance_model_nickname_a**) and `finance_model_c` (defined by **finance_model_nickname_c**).
    - **tech_b** and **tech_c**: technology keys in `tech_config['technologies']`, the costs of these technologies are included in the financial calculation done in `finance_model_c`.
    - **finance_model_nickname_a** and **finance_model_nickname_c**: the nickname(s) of the finance model and corresponding inputs to use for **subgroup_c** finance calculations.
- naming convention:
  - **subgroup_a** outputs: suppose `finance_model_a` outputs `price` parameter.
    - `financials_subgroup_<subgroup_a>.price_<commodity_a>_<desc_a>`
  - **subgroup_b** outputs: suppose `finance_model_a` outputs `price` parameter.
    - `financials_subgroup_<subgroup_b>.price_<commodity_a>_<desc_b>_<finance_model_nickname_a>`
    - `financials_subgroup_<subgroup_b>.price_<commodity_a>_<desc_b>_<finance_model_nickname_b>`
  - **subgroup_c** outputs: suppose `finance_model_a` outputs `price` parameter and `finance_model_c` outputs `NPV` parameter.
    - `financials_subgroup_<subgroup_c>.NPV_<commodity_b>_<finance_model_nickname_a>`
    - `financials_subgroup_<subgroup_c>.NPV_<commodity_b>_<finance_model_nickname_c>`
    - `financials_subgroup_<subgroup_c>.price_<commodity_b>_<finance_model_nickname_a>`
    - `financials_subgroup_<subgroup_c>.price_<commodity_b>_<finance_model_nickname_c>`

- examples that use this format:
  - [Example 10](https://github.com/NREL/H2Integrate/blob/develop/examples/10_electrolyzer_om/plant_config.yaml)
