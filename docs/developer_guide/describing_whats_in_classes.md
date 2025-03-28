# Expected methods and attributes of classes

Within each technology class, H2Integrate expects certain methods to be defined by the developer.
This doc page briefly discusses those methods and their impact within H2Integrate.

## Performance model

Each technology class must define `get_performance_model()`, which returns an OpenMDAO system.
This system contains the physics model for the technology.
For a converter, this computes the outputted resources based on the inputted resources.
The input and output resources for the performance model are all arrays with length 8760 for hourly timestepped yearly data.

For example, for an electrolyzer, the performance model is an OpenMDAO system whose inputs include electricity and whose outputs include hydrogen produced.

## Cost model

Each technology class must also define `get_cost_model()`, which returns an OpenMDAO system containing the cost model.
Specifically, this system must output `CapEx` and `OpEx` values for the technology.
These values are later used in financial modeled and cost breakdowns.

## Financial model (optional)

Each technology class can define `get_financial_model()`, which returns an OpenMDAO system containing the financial model.
This would override any plant level financial model, and is useful for technologies that have unique financial considerations.
This will also be more relevant as we develop non-single-owner capabilities.

## Control model (optional, unused)

Each technology class can define `get_control_strategy()`.
We do not currently use this method and instead use a top-level control strategy.
In the future, individual technologies may have unique control strategies.

```{note}
It is possible to have a combined performance, cost, and financial model within a single OpenMDAO system, provided that it returns all the necessary values.
For example, in the HOPP wrapper, we use a combined performance and cost model to reduce computational cost.
```
