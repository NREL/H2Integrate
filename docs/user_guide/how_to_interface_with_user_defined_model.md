# Custom User Defined Model

## Overview

H2Integrate now supports **user-defined models** that operate alongside built-in wrapped models for performance, cost, and financial analysis. This feature enables users to integrate proprietary or external tools with the H2Integrate framework, unlocking more flexible and extensible workflows.

## Why Use Custom Models?

Users may want to:
- Use proprietary models developed in-house.
- Integrate with tools outside of H2Integrate (e.g., Aspen, Excel, or custom Python code).
- Model technologies not yet covered by existing wrapped models.

This feature allows any custom model that conforms to OpenMDAO standards and uses the appropriate configuration interfaces to be used within the H2Integrate ecosystem.

## Example: Paper Mill Model

To demonstrate this capability, we include a minimal example of a custom model: a **paper mill**. This example includes:

- A `PaperMillPerformance` model that converts electricity input to paper output.
- A `PaperMillCost` model that estimates capital and operational expenditures.
- A `PaperMillFinance` model that computes the levelized cost of paper production (LCOP).

These models use standard H2Integrate configuration utilities and OpenMDAO components.

```{note}
You can combine an H2Integrate model and a custom model for the same technology within a single analysis.
```

## Key Benefits

- **Flexibility**: Use any modeling tool or codebase that suits your domain or organization.
- **Interoperability**: Integrate with the broader H2Integrate pipeline, including downstream analyses.
- **Confidentiality**: Keep proprietary models external to the H2Integrate codebase.

## Key Concepts

- **Custom models are defined as OpenMDAO components.**
- **Configuration is handled using `attrs` and `BaseConfig`** for consistent validation and input/output management.
- **Inputs and outputs should follow standard naming and unit conventions** where applicable.
- **Models can be integrated into the broader H2Integrate workflow**, including scenario execution and results processing.

## Getting Started

To use a custom model in your H2Integrate project:

1. **Create Configuration Classes**

   Subclass `BaseConfig` for any performance, cost, or financial parameters your model needs.

2. **Implement OpenMDAO Components**

   Define your model logic using `om.ExplicitComponent`.

3. **Merge Inputs**

   Use `merge_shared_performance_inputs` and `merge_shared_cost_inputs` to integrate with existing input structures.

4. **Use in a Pipeline**

   Treat your custom model as a drop-in component in your analysis pipeline.

```{note}
Custom models can include external calls—for example, to an Excel macro—within the `compute` function, as long as the required inputs and outputs are properly defined and handled.
```

Refer to the [Paper Mill Model Example](https://github.com/NREL/H2Integrate/tree/main/examples/06_custom_tech/) for a complete walkthrough.
---

This enhancement supports broader adoption of H2I by allowing integration with the tools and models users already trust.
