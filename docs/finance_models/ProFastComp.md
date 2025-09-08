
(profastcomp:profastcompmodel)=
# ProFastComp
The ``"ProFastComp"`` finance model calculates levelized cost of commodity using ProFAST.

The inputs, outputs, and naming convention for the `ProFastComp` model are outlined in this section.
- [Input parameters](profastcomp:overview)
  - [H2Integrate format](profastcomp:direct_opt)
  - [ProFAST format](profastcomp:pf_params_opt)
  - [Override defaults for specific technologies](profastcomp:tech_specific_finance)
- [Output values and naming convention](profastcomp:outputs)


(profastcomp:overview)=
## Finance parameters overview
The main inputs for `ProFastComp` model include:
- optional: information to export the ProFAST config to a .yaml file
- required: financial parameters (`params` section). These can be input in the `ProFastComp` format or the `ProFAST` format. These two formats are described in the following sections:
  - [ProFastComp format](profastcomp:direct_opt)
  - [ProFAST format](profastcomp:pf_params_opt)
- required: default capital item parameters (`capital_items` section). These parameters can be over-written for specific technologies if specified in the `tech_config`. Example usage of over-writing values in the `tech_config` is outlined [here](profastcomp:tech_specific_finance)

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

(profastcomp:direct_opt)=
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

(profastcomp:pf_params_opt)=
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

(profastcomp:tech_specific_finance)=
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

(profastcomp:outputs)=
## Output values and naming convention
``ProFastComp`` outputs the following data:
- `LCO<x_and_descriptor>`: levelized cost of commodity in USD/commodity unit.
- `wacc_<commodity_and_descriptor>`: weighted average cost of capital as a fraction.
- `crf_<commodity_and_descriptor>`: capital recovery factor as a fraction.
- `irr_<commodity_and_descriptor>`: internal rate of return as a fraction.
- `profit_index_<commodity_and_descriptor>`
- `investor_payback_period_<commodity_and_descriptor>`: time until initial investment costs are recovered in years.
- `price_<commodity_and_descriptor>`: first year price of commodity in same units as levelized cost.

**Naming convention**:
- `<commodity_and_descriptor>`:
  - if `commodity_desc` is **not** provided, then `<commodity_and_descriptor>` this is just `commodity`. For example, `wacc_hydrogen` if the `commodity` is `"hydrogen"`.
  - if `commodity_desc` is provided, then `<commodity_and_descriptor>` is `<commodity>_<commodity_desc>`. For example, `wacc_hydrogen_produced` if the `commodity` is `"hydrogen"` and `commodity_desc` is `"produced"`
- `<x_and_descriptor>`:
  - if `commodity_desc` is **not** provided, then `<x_and_descriptor>` is the upper-case first letter of the `commodity`. For example, `LCOH` if the `commodity` is `"hydrogen"`
  - if `commodity_desc` is provided, then `<x_and_descriptor>` is the upper-case first letter of the `commodity` followed by the `commodity_desc` descriptor. For example, `LCOH_produced` if the `commodity` is `"hydrogen"` and the `commodity_desc` is `"produced"`.
