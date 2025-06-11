# Custom user-defined models

## Overview

H2Integrate now supports **user-defined models** that operate alongside built-in wrapped models for performance, cost, and financial analysis. This feature enables users to integrate proprietary or external tools with the H2Integrate framework, unlocking more flexible and extensible workflows.

## Why use custom models?

Users may want to:
- Use proprietary models developed in-house.
- Integrate with tools outside of H2Integrate (e.g., Aspen, Excel, or custom Python code).
- Model technologies not yet covered by existing wrapped models.

This feature allows any custom model that conforms to OpenMDAO standards and uses the appropriate configuration interfaces to be used within the H2Integrate ecosystem.

## Example: paper mill model

To demonstrate this capability, we include a minimal example of a custom model: a **paper mill**. This example includes:

- A `PaperMillPerformance` model that converts electricity input to paper output.
- A `PaperMillCost` model that estimates capital and operational expenditures.
- A `PaperMillFinance` model that computes the levelized cost of paper production (LCOP).

These models use standard H2Integrate configuration utilities and OpenMDAO components.

```{note}
You can combine an H2Integrate model and a custom model for the same technology within a single analysis.
```

## Key benefits

- **Flexibility**: Use any modeling tool or codebase that suits your domain or organization.
- **Interoperability**: Integrate with the broader H2Integrate pipeline, including downstream analyses.
- **Confidentiality**: Keep proprietary models external to the H2Integrate codebase.

## Key concepts

- **Custom models are defined as OpenMDAO components.**
- **Configuration is handled using `attrs` and `BaseConfig`** for consistent validation and input/output management.
- **Inputs and outputs should follow standard naming and unit conventions** where applicable.
- **Models can be integrated into the broader H2Integrate workflow**, including scenario execution and results processing.

## Getting started

To use a custom model in your H2Integrate project, we recommend you look at existing models in the H2Integrate codebase to help guide the process.
Then you can follow these steps:

1. **Create configuration classes**

   Create a configuration class that inherits from `BaseConfig` for any performance, cost, or financial parameters your model needs.

2. **Implement OpenMDAO components**

   Define your model logic using `om.ExplicitComponent`.

3. **Merge inputs**

   Use `merge_shared_inputs` to integrate with existing input structures.

4. **Use in a workflow**

   Treat your custom model as a drop-in component in your analysis workflow.

```{note}
Custom models can include calls to external tools (e.g. an Excel macro) within the `compute` function as long as the required inputs and outputs are properly defined and handled.
```

Refer to the [Paper Mill Model Example](https://github.com/NREL/H2Integrate/tree/develop/examples/06_custom_tech/) for a complete walkthrough.

This feature supports broader adoption of H2I by allowing integration with the tools and models users already trust.
