# Solar-PV Cost Models based on ATB-Formatted Cost Data

NREL's [Annual Technology Baseline](https://atb.nrel.gov/electricity/2024/data) (ATB) is commonly referenced for technology costs such as overnight capital cost, fixed operations and maintenance costs, and capital expenditures. Two solar-PV cost models are available in H2I that are intended to be easily used with cost values pulled from [NREL's ATB Excel workbook](https://atb.nrel.gov/electricity/2024/data).

As mentioned on the [Utility-Scale PV ATB page](https://atb.nrel.gov/electricity/2024/utility-scale_pv), the costs for utility-scale PV have been published in `$/kW-AC` since 2020. The costs for [Commerical PV](https://atb.nrel.gov/electricity/2024/commercial_pv) and [Residential PV](https://atb.nrel.gov/electricity/2024/residential_pv) remain to be published in `$/kW-DC`. The main different in the two cost models are whether costs are input in `$/kW-AC` or `$/kW-DC`.

- The `"atb_utility_pv_cost"` cost model has costs input in `$/kW-AC` and is input the PV capacity in kW-AC from the output of the PV performance model. Example usage of this cost model in the `tech_config.yaml` file is shown [here](#utility-scale-pv-cost-model)
- The `"atb_com_res_pv_cost"` cost model has costs input in `$/kW-DC` and is input the PV capacity in kW-DC from the **shared input parameter** of the PV performance model. Example usage of this cost model in the `tech_config.yaml` file is shown [here](#commercial-and-residential-pv-cost-model)

### Utility-Scale PV Cost Model

The inputs for `cost_parameters` are `capex_per_kWac` and `opex_per_kWac_per_year`. From the ATB workbook, a value for `capex_per_kWac` can be found on the `Solar - Utility PV` sheet under the "Overnight Capital Cost" section or the "CAPEX" section. The values in the "CAPEX" section include overnight capital costs, construction finance factor, and grid connection costs. A value for `opex_per_kWac_per_year` can be found on the `Solar - Utility PV` sheet under the "Fixed Operation and Maintenance Expenses" section.

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
```

### Commercial and Residential PV Cost Model
The inputs for `cost_parameters` are `capex_per_kWdc` and `opex_per_kWdc_per_year`. From the ATB workbook, a value for `capex_per_kWdc` can be found on the `Solar - PV Dist. Comm` or `Solar - PV Dist. Res` sheet under the "Overnight Capital Cost" section or the "CAPEX" section. The values in the "CAPEX" section include overnight capital costs, construction finance factor, and grid connection costs. A value for `opex_per_kWdc_per_year` can be found on the `Solar - PV Dist. Comm` or `Solar - PV Dist. Res` sheet under the "Fixed Operation and Maintenance Expenses" section.

```yaml
technologies:
  solar:
    performance_model:
      model: "pysam_solar_plant_performance"
    cost_model:
      model: "atb_com_res_pv_cost"
    model_inputs:
        shared_parameters:
            pv_capacity_kWdc: 200
        performance_parameters:
            dc_ac_ratio: 1.23
            create_model_from: "default"
            config_name: "PVWattsCommercial"
        cost_parameters:
            capex_per_kWdc: 1439
            opex_per_kWdc_per_year: 16
```
