# Finance Parameters

Finance parameters are primarily specified in the `plant_config` under the `finance_parameters` section.
The `plant_life` parameter from the `plant` section of the `plant_config` is also used in finance calculations.

There are two approaches for specifying other finance parameters:
- [Directly in finance parameters](finance:direct_opt)
- [ProFAST parameters config](finance:pf_params_opt)

Both approaches require the following additional finance parameters to be specified:
- `cost_year_adjustment_inflation` is used to adjust costs for each technology from the cost year of the technology model (see [details on cost years and cost models here](#cost-year-of-cost-models)) to the `target_dollar_year` specified in the `plant_config` under the `finance_parameters` section.
- `depreciation_method`: depreciation method to apply to capital items
- `depreciation_period`: depreciation period (in years) for capital items (except electrolyzer, if used)
- `depreciation_period_electrolyzer`: depreciation period (in years) for electrolyzer capital item (if used)

(finance:direct_opt)=
## Providing Finance Parameters: Direct Method
Below is an example inputting financial parameters directly in the `finance_parameters` section of `plant_config`:

```yaml
finance_parameters:
  analysis_start_year: 2032 #year that financial analysis starts
  installation_time: 36 #installation period in months
  # Inflation parameters
  inflation_rate: 0.0 # 0 for nominal analysis
  # Finance parameters
  discount_rate: 0.09
  debt_equity_split: False
  debt_equity_ratio: 2.62
  property_tax: 0.02
  property_insurance: 0.01
  total_income_tax_rate: 0.257
  capital_gains_tax_rate: 0.15
  sales_tax_rate: 0.07375
  debt_interest_rate: 0.07
  debt_type: "Revolving debt"
  loan_period: 0
  cash_onhand_months: 1
  administrative_expense_percent_of_sales: 0.00
  # Capital item depreciation parameters
  depreciation_method: "MACRS"
  depreciation_period: 5
  depreciation_period_electrolyzer: 7
  # To adjust costs for technologies to target_dollar_year
  cost_adjustment_parameters:
    target_dollar_year: 2022
    cost_year_adjustment_inflation: 0.025
```

This approach also relies on data from `plant_config`:
- `plant_life`: used as the `operating life` ProFAST parameter
- `installation_time`: used as the `installation months` ProFAST parameter


```{note}
`inflation_rate` is used to populate the escalation and inflation rates in ProFAST entries with a value of 0 corresponding to a *nominal analysis*.
```


**Debt Equity Ratio vs Debt Equity Split**

If `debt_equity_split` is False, the debt equity ratio is set as the value specified by `debt_equity_ratio`. If `debt_equity_ratio` is False, the debt equity ratio is calculated based on the value specified by `debt_equity_split`. The relationship between debt equity ratio and debt equity split is given below:

$\text{debt equity ratio} = \frac{\text{debt equity split}}{100 - \text{debt equity split}}$

$\text{debt fraction} = \frac{\text{debt equity ratio}}{\text{debt equity ratio + 1}}$

$\text{equity fraction} = 1 - \text{debt fraction}$

(finance:pf_params_opt)=
## Providing Finance Parameters: ProFAST params config file

```{note}
To avoid errors, please check that `plant_config['plant']['plant_life']` is equal to `plant_config['finance_parameters']['pf_params']['params']['operating life']` and that `plant_config['finance_parameters']['installation_time']` is equal to `plant_config['finance_parameters']['pf_params']['params']['installation months']`


| plant config parameter | equivalent `pf_params` parameter |
| -------- | ------- |
| `plant['plant']['plant_life']` | `operating life` |
| `plant['finance_parameters'][installation_time]` | `installation months` |
```

Below is an example of the `finance_parameters` section of `plant_config` if using `pf_params` format to specify financial parameters:

```yaml
finance_parameters:
  analysis_start_year: 2032
  installation_time: 36
  pf_params: !include "profast_params.yaml" #Finance information
  depreciation_method: "MACRS" #depreciation method for capital items
  depreciation_period: 5 #depreciation period for capital items
  depreciation_period_electrolyzer: 7 #depreciation period for electrolyzer
  cost_adjustment_parameters:
    target_dollar_year: 2022
    cost_year_adjustment_inflation: 0.025 # used to adjust costs for technologies to target_dollar_year
```

Below is an example of a valid `pf_params` config that may be specified in the `finance_parameters` section of `plant_config`:
```yaml
params:
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
  operating life: 30
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
| `h2_storage` for geologic storage or buried pipe | ? 2018 ? |
| `simple_ammonia_cost`   |  2022    |
| `direct_ocean_capture_cost` | 2023 |
| `steel_cost`            |  2022    |
| `reverse_osmosis_desalination_cost` | ? 2013 ? |
| `synloop_ammonia_cost`  |  N/A (adjusts costs to `target_dollar_year` within cost model)  |


## Cost models with user input cost year

### Summary of cost models that have user-input cost year
| Cost Model              | Cost Year  |
| :---------------------- | :---------------: |
| `wind_plant_cost` |  user-input    |
| `atb_utility_pv_cost` |  user-input    |
| `atb_comm_res_pv_cost` |  user-input    |
| `simple_ASU_cost` |  user-input |
| `hopp`            | user-input  |
| `run_of_river_hydro_cost` | user-input  |
| `smr_methanol_plant_cost` | user-input  |
| `stimulated_geoh2_cost` | user-input  |
| `natural_geoh2_cost`    | user-input  |
| `wombat`                | user-input  |
| `hydrogen_tank_cost`    | user-input  |

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
