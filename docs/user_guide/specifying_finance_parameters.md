# Finance Parameters

The finance model, finance model specific inputs, and cost adjustment information (regardless of the finance model) are required in the `finance_parameters` of the `plant_config`.

```{note}
The `plant_life` parameter from the `plant` section of the `plant_config` is also used in finance calculations as the operating life of the plant.
```

The finance parameters section requires the following information:
- `finance_model`: name of the finance model. Current finance model options include:
  - [`'ProFastComp'`](finance:profastcompmodel): calculates levelized cost of commodity using ProFAST
- `model_inputs`: inputs that are specific to the finance model
- `cost_adjustment_parameters`:
  - `target_dollar_year`: dollar-year to convert costs to.
  - `cost_year_adjustment_inflation` is used to adjust costs for each technology from the cost year of the technology model (see [details on cost years and cost models here](#cost-year-of-cost-models)) to the `target_dollar_year`

(finance:profastcompmodel)
# Finance Parameters: ProFastComp
The inputs for the `ProFastComp` model are outlined in this section:

(finance:overview)=
## Finance parameters overview
The main inputs for `ProFastComp` model include:
- optional: information to export the ProFAST config to a .yaml file
- required: financial parameters (`params` section). These can be input in the `ProFastComp` format or the `ProFAST` format. These two formats are described in the following sections:
  - [ProFastComp format](finance:direct_opt)
  - [ProFAST format](finance:pf_params_opt)
- required: default capital item parameters (`capital_items` section). These parameters can be over-written for specific technologies if specified in the `tech_config`. Example usage of over-writing values in the `tech_config` is outlined [here](finance:tech_specific_finance)

```yaml
finance_parameters:
  finance_model: "ProFastComp"
  model_inputs: #inputs for the finance_model
    save_profast_to_file: True #optional, will save ProFAST entries to .yaml file in the folder specified in the driver_config (`driver_config["general"]["folder_output"]`)
    profast_output_description: "profast_config" #required if `save_profast_to_file` is True, used to name the output file.
    params: #Financial parameters section
    capital_items: #Required: section for default parameters for capital items
      depr_type: "MACRS" #Required: depreciation method for capital items, can be "MACRS" or "Straight line"
      depr_period: 5 #Required: depreciation period for capital items
      refurb: [0.] #Optional: replacement schedule as a fraction of the capital cost. Defaults to [0.]
    fixed_costs: #Optional section for default parameters for fixed cost items
      escalation: #escalation rate for fixed costs, will default to `inflation_rate` specific in the params section
      unit: "$/year" #optional unit of the cost. Defaults to $/year
      usage: 1.0 #usage multiplier, most commonly is set to 1 and defaults to 1.0

```

(finance:direct_opt)=
## Providing Finance Parameters: ProFastComp Format
Below is an example inputting financial parameters directly in the `finance_parameters` section of `plant_config`:

```yaml
finance_parameters:
  finance_model: "ProFastComp" #finance model
    model_inputs: #inputs for finance_model
      params: #Financing parameters
        analysis_start_year: 2032 #year that financial analysis starts
        installation_time: 36 #installation period in months
        # Inflation parameters
        inflation_rate: 0.0 # 0 for nominal analysis
        # Finance parameters
        discount_rate: 0.09
        debt_equity_ratio: 2.62
        property_tax_and_insurance: 0.03
        total_income_tax_rate: 0.257
        capital_gains_tax_rate: 0.15
        sales_tax_rate: 0.07375
        debt_interest_rate: 0.07
        debt_type: "Revolving debt" #"Revolving debt" or "One time loan"
        loan_period_if_used: 0 #loan period if debt_type is 'One time loan'
        cash_onhand_months: 1
        admin_expense: 0.00 #administrative expense as a fraction of sales
    #default parameters for capital items unless specified in tech_config
    capital_items:
      depr_type: "MACRS" #depreciation method for capital items, can be "MACRS" or "Straight line"
      depr_period: 5 #depreciation period for capital items in years.
      refurb: [0.] #refurbishment schedule, values represent the replacement cost as a fraction of the CapEx

  # To adjust costs for technologies to target_dollar_year
  cost_adjustment_parameters:
    target_dollar_year: 2022
    cost_year_adjustment_inflation: 0.025
```

This approach also relies on data from `plant_config`:
- `plant_life`: used as the `operating life` ProFAST parameter


```{note}
`inflation_rate` is used to populate the escalation and inflation rates in ProFAST entries with a value of 0 corresponding to a *nominal analysis*.
```

(finance:pf_params_opt)=
## Providing Finance Parameters: ProFAST format

```{note}
To avoid errors, please check that `plant_config['plant']['plant_life']` is equal to `plant_config['finance_parameters']['model_inputs']['params']['operating life']`. Or remove `operating life` from the finance parameter inputs.`


| plant config parameter | equivalent `params` parameter |
| -------- | ------- |
| `plant['plant']['plant_life']` | `operating life` |
```

Below is an example of the `finance_parameters` section of `plant_config` if using ProFAST input format to specify financial parameters:

```yaml
finance_parameters:
  finance_model: "ProFastComp"
  model_inputs:
    params: !include  "profast_params.yaml" #Finance information
    capital_items: #default parameters for capital items unless specified in tech_config
      depr_type: "MACRS" ##depreciation method for capital items, can be "MACRS" or "Straight line"
      depr_period: 5 #depreciation period for capital items
      refurb: [0.]
  cost_adjustment_parameters:
    target_dollar_year: 2022
    cost_year_adjustment_inflation: 0.025 # used to adjust costs for technologies to target_dollar_year
```

Below is an example of a valid ProFAST params config that may be specified in the `finance_parameters['model_inputs']['params]` section of `plant_config`:
```yaml
# Installation information
maintenance:
  value: 0.0
  escalation: 0.0
non depr assets: 250000 #such as land cost
end of proj sale non depr assets: 250000 #such as land cost
installation cost:
  value: 0.0
  depr type: "Straight line"
  depr period: 4
  depreciable: False
# Incentives information
incidental revenue:
  value: 0.0
  escalation: 0.0
annual operating incentive:
  value: 0.0
  decay: 0.0
  sunset years: 0
  taxable: true
one time cap inct:
  value: 0.0
  depr type: "MACRS"
  depr period: 5
  depreciable: True
# Sales information
analysis start year: 2032
operating life: 30 #if included, should equal plant_config['plant']['plant_life']
installation months: 36
demand rampup: 0
# Take or pay specification
TOPC:
  unit price: 0.0
  decay: 0.0
  support utilization: 0.0
  sunset years: 0
# Other operating expenses
credit card fees: 0.0
sales tax: 0.0
road tax:
  value: 0.0
  escalation: 0.0
labor:
  value: 0.0
  rate: 0.0
  escalation: 0.0
rent:
  value: 0.0
  escalation: 0.0
license and permit:
  value: 0.0
  escalation: 0.0
admin expense: 0.0
property tax and insurance: 0.015
# Financing information
sell undepreciated cap: True
capital gains tax rate: 0.15
total income tax rate: 0.2574
leverage after tax nominal discount rate: 0.0948
debt equity ratio of initial financing: 1.72
debt interest rate: 0.046
debt type: "Revolving debt"
general inflation rate: 0.0
cash onhand: 1 # number of months with cash on-hand
tax loss carry forward years: 0
tax losses monetized: True
loan period if used: 0
```

(finance:tech_specific_finance)=
## Over-ride defaults for specific technologies

Capital item entries can be over-written for individual technologies.

#### **Over-write depreciation period:**

Suppose the default depreciation period for capital items is 5 years (set in the `plant_config['finance_parameters']['model_inputs]['capital_items']['depr_period']`), but we want the depreciation period for the electrolyzer to be 7 years. This can be done in the `tech_config` as shown below:
```yaml
technologies:
  electrolyzer:
    model_inputs:
      finance_parameters:
        capital_items:
          depr_period: 7
```


#### **Custom refurbishment period:**

Suppose the default refurbishment schedule for capital items is `[0.]` (set in the `plant_config['finance_parameters']['model_inputs]['capital_items']['refurb']`), but we want our battery to be replaced in 15-years and the replacement cost is equal to the capital cost. This can be accomplished in the tech_config as shown below:
```yaml
technologies:
  battery:
    model_inputs:
      finance_parameters:
        capital_items:
          refurbishment_period_years: 15
          replacement_cost_percent: 1.0
```


# Cost year of Cost Models
Some cost models are derived from literature and output costs (CapEx and OpEx) in a specific dollar-year. Some cost models require users to input the key cost information, and the output costs are in the same cost year as the user-provided costs. For [cost models with a built-in cost year](#cost-models-with-inherent-cost-year), the cost year is not required as an input for the cost model. For [cost models based on user provided costs](#cost-models-with-user-input-cost-year), the `cost_year` should be included in the tech_config for that technology.

## Cost models with inherent cost year

### Summary of cost models that are based around a cost year
| Cost Model              | Cost Year  |
| :---------------------- | :---------------: |
| `basic_electrolyzer_cost`|  2016    |
| `pem_electrolyzer_cost`|  2021    |
| `singlitico_electrolyzer_cost`|  2021    |
| `h2_storage`  with `'mch'` storage type  |  2024    |
| `h2_storage` for geologic storage or buried pipe | 2018 |
| `simple_ammonia_cost`   |  2022    |
| `direct_ocean_capture_cost` | 2023 |
| `ocean_alkalinity_enhancement_cost` | 2024 |
| `ocean_alkalinity_enhancement_cost_financial` | 2024 |
| `steel_cost`            |  2022    |
| `reverse_osmosis_desalination_cost` | 2013 |
| `synloop_ammonia_cost`  |  N/A (adjusts costs to `target_dollar_year` within cost model)  |


## Cost models with user input cost year

### Summary of cost models that have user-input cost year
| Cost Model              |
| :---------------------- |
| `wind_plant_cost` |
| `atb_utility_pv_cost` |
| `atb_comm_res_pv_cost` |
| `simple_ASU_cost` |
| `hopp`            |
| `run_of_river_hydro_cost` |
| `smr_methanol_plant_cost` |
| `stimulated_geoh2_cost` |
| `natural_geoh2_cost`    |
| `wombat`                |
| `hydrogen_tank_cost`    |
| `custom_electrolyzer_cost` |

### Example tech_config input for user-input cost year
```yaml
technologies:
  solar:
    performance_model:
      model: "pysam_solar_plant_performance"
    cost_model:
      model: "atb_utility_pv_cost"
    model_inputs:
        performance_parameters:
            pv_capacity_kWdc: 100000
            dc_ac_ratio: 1.34
            ...
        cost_parameters:
            capex_per_kWac: 1044
            opex_per_kWac_per_year: 18
            cost_year: 2022

```
