# Finance Parameters

The finance model, finance model specific inputs, and cost adjustment information (regardless of the finance model) are required in the `finance_parameters` of the `plant_config`.

```{note}
The `plant_life` parameter from the `plant` section of the `plant_config` is also used in finance calculations as the operating life of the plant.
```

The `finance_parameters` section requires the following information:
- `cost_adjustment_parameters`:
  - `target_dollar_year`: dollar-year to convert costs to.
  - `cost_year_adjustment_inflation` is used to adjust costs for each technology from the cost year of the technology model (see [details on cost years and cost models here](cost:cost_years) to the `target_dollar_year`

Other common variables to include in the `finance_parameters` section are:
- **finance_model** (string): Name of the general financial model to use. This should not be a technology specific finance model.
- **model_inputs** (dictionary): Input parameters for `finance_model`
- **commodity** (str): The commodity used for calculations in the `finance_model`
- **commodity_desc** (str): Optional additional description of the commodity.


## Not specifying subgroups
no specified subgroups means you have to use 1 finance model and one commodity.

General format:
```yaml
finance_parameters:
  commodity: "commodity_a"
  finance_model: "finance_model_a" #ex: "ProFastComp"
  model_inputs: #dictionary of inputs for finance_model_a
```
- **commodity_a**: a commodity produced by at least one technology in `tech_config`. Ex: "hydrogen".
- **finance_model_a**: a general finance model. Ex: "ProFastComp".

- output naming convention:
  - `financials_subgroup_default.<finance_model_a_output>`
- examples that use this format:
  - [Example 7](/examples/07_run_of_river_plant/plant_config.yaml)
- assumptions and logic:
  - the financial model will include costs from all technologies in the `tech_config`


## Single financial model with subgroups

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

- naming convention: `financials_subgroup_default.<finance_model_a_output>`
- examples that use this format:
  - [Example 02](/examples/02_texas_ammonia/plant_config.yaml)
  - [Example 03 - CO2H](/examples/03_methanol/co2_hydrogenation/plant_config_co2h.yaml)
  - [Example 05](/examples/)
  - 11, 12, 13, 14, 15, 17
  - [Example 09 - OAE](/examples/09_co2/ocean_alkalinity_enhancement/plant_config.yaml)
  - [Example 09 - DOC](/examples/09_co2/direct_ocean_capture/plant_config.yaml)
  - [Example 09 - OAE Financials](/examples/09_co2/ocean_alkalinity_enhancement_financials/plant_config_financials.yaml)
- assumptions and logic:

## Nicknamed financial model with subgroups
This is an alternative format to [above](#single-financial-model-with-subgroups) that highlights some logic for [specifying multiple finance models](#multiple-financial-models-with-subgroups)

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

- output naming convention:
  - `financials_subgroup_<subgroup_a>.<a_output_of_>`
  - `financials_subgroup_<subgroup_b>.<finance_model_a_output>`
- examples that use this format:
  - [Example 01](/examples/01_onshore_steel_mn/plant_config.yaml)
- assumptions and logic:
  - `subgroup_a`

## Multiple financial models with subgroups
multiple financial models and/or multiple commodity types

General format:
```yaml
finance_parameters:
  finance_model_nickname_a:
    finance_model: "finance_model_a" #ex: "ProFastComp"
    model_inputs: #dictionary of inputs for the finance_model_a
  finance_model_nickname_b:
    finance_model: "finance_model_a" #ex: "ProFastComp"
    model_inputs: #dictionary of inputs for finance_model_a
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
- naming convention:
  - `financials_subgroup_<subgroup_a>.price_<commodity_a>_<desc_a>`
  - `financials_subgroup_<subgroup_b>.price_<commodity_a>_<desc_b>_<finance_model_nickname_a>`
  - `financials_subgroup_<subgroup_b>.price_<commodity_a>_<desc_b>_<finance_model_nickname_b>`
  - `financials_subgroup_<subgroup_c>.NPV_<commodity_b>_<finance_model_nickname_a>`
  - `financials_subgroup_<subgroup_c>.NPV_<commodity_b>_<finance_model_nickname_c>`
- examples that use this format:
  - [Example 10](/examples/10_electrolyzer_om/plant_config.yaml)
- assumptions and logic:
