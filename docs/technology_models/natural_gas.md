# Natural gas power plant model

The natural gas power plant model simulates electricity generation from natural gas combustion, suitable for both natural gas combustion turbines (NGCT) and natural gas combined cycle (NGCC) plants. The model calculates electricity output based on natural gas input and plant heat rate, along with comprehensive cost modeling that includes capital expenses, operating expenses, and fuel costs.

The model is implemented as two components: a performance model that converts natural gas fuel input to electricity output, and a cost model that calculates capital and operating costs over the plant lifetime.

To use this model, specify `"natural_gas_performance"` as the performance model and `"natural_gas_cost"` as the cost model. An example of how this may look in the `tech_config` file is shown below:

```yaml
technologies:
    ngcc_plant:
        performance_model: "natural_gas_performance"
        cost_model: "natural_gas_cost"
        model_inputs:
            performance_parameters:
                heat_rate: 7.5  # MMBtu/MWh - high efficiency for NGCC
            cost_parameters:
                capex: 1000     # $/kW - capital cost
                fopex: 10.0     # $/kW/year - fixed O&M
                vopex: 2.5      # $/MWh - variable O&M
                heat_rate: 7.5  # MMBtu/MWh - must match performance
                ng_price: 4.2   # $/MMBtu
                project_life: 30  # years
                cost_year: 2023
```

## Performance Parameters

The performance model requires the following parameter:

- `heat_rate` (required): Heat rate of the natural gas plant in MMBtu/MWh. This represents the amount of fuel energy required to produce one MWh of electricity. Lower values indicate higher efficiency. Typical values:
  - **NGCC (Combined Cycle)**: 6-8 MMBtu/MWh (high efficiency)
  - **NGCT (Combustion Turbine)**: 10-14 MMBtu/MWh (lower efficiency, faster response)

The model implements the relationship:

$$
\text{Electricity Output (MW)} = \frac{\text{Natural Gas Input (MMBtu/h)}}{\text{Heat Rate (MMBtu/MWh)}}
$$

## Cost Parameters

The cost model calculates capital and operating costs based on the following parameters:

- `capex` (required): Capital cost per unit capacity in $/kW. This includes all equipment, installation, and construction costs. Typical values:
  - **NGCT**: 600-1000 $/kW (lower capital cost)
  - **NGCC**: 800-1200 $/kW (higher capital cost)

- `fopex` (required): Fixed operating expenses per unit capacity in $/kW/year. This includes fixed O&M costs that don't vary with generation. Typical values: 5-15 $/kW/year

- `vopex` (required): Variable operating expenses per unit generation in $/MWh. This includes variable O&M costs that scale with electricity generation. Typical values: 1-5 $/MWh

- `heat_rate` (required): Heat rate in MMBtu/MWh, used for fuel cost calculations. This should match the heat rate used in the performance model.

- `ng_price` (required): Natural gas price in $/MMBtu. Can be a numeric value for fixed price or `"variable"` string to indicate external price management.

- `project_life` (optional): Project lifetime in years for cost calculations. Default is 30 years, typical for power plants.

- `cost_year` (required): Dollar year corresponding to input costs.

## Cost Calculation

The model calculates total costs as follows:

1. **Capital Expenditure (CapEx)**:
   $$\text{CapEx} = \text{capex} \times \text{Plant Capacity (kW)}$$

2. **Operating Expenditure (OpEx)** over project lifetime:
   $$\text{OpEx} = \text{Fixed O\&M} + \text{Variable O\&M} + \text{Fuel Costs}$$

   Where:
   - Fixed O&M = `fopex` × Plant Capacity (kW) × Project Life (years)
   - Variable O&M = `vopex` × Annual Generation (MWh) × Project Life (years)
   - Fuel Costs = `ng_price` × `heat_rate` × Annual Generation (MWh) × Project Life (years)

## Technology Applications

### Natural Gas Combined Cycle (NGCC)
- **Use case**: Baseload or intermediate power generation
- **Characteristics**: High efficiency, lower operating costs, higher capital costs, longer startup times
- **Typical heat rate**: 6-8 MMBtu/MWh
- **Typical capacity factor**: 50-80%

### Natural Gas Combustion Turbine (NGCT)
- **Use case**: Peaking power generation, grid balancing
- **Characteristics**: Lower efficiency, higher operating costs, lower capital costs, fast startup and ramping
- **Typical heat rate**: 10-14 MMBtu/MWh
- **Typical capacity factor**: 10-30%

## Variable Natural Gas Pricing

For cases where natural gas prices vary over time and are handled externally (e.g., through optimization or time-series data), set `ng_price: "variable"`. When this option is used, fuel costs are set to zero in the cost model, allowing external management of fuel pricing.

```yaml
cost_parameters:
    # ... other parameters ...
    ng_price: "variable"  # Indicates external price management
```

## OpenMDAO Integration

All model parameters are implemented as OpenMDAO inputs, making them available for optimization, uncertainty quantification, and parameter studies. The configuration values serve as default values, but can be overridden at runtime through the OpenMDAO interface.

This enables advanced workflows such as:
- Natural gas price optimization
- Plant sizing optimization
- Heat rate sensitivity studies
- Multi-objective optimization balancing capital costs and efficiency
