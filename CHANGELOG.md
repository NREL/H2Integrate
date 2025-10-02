# CHANGELOG

## 0.3.1, Unreleased, TBD
- Added rule-based storage system control capability
- Bugfix: only run pyxdsm when there are connections in the system
- Added *_out/ to .gitignore to avoid clutter
- Added methanol production base class
- Added steam methane reforming methanol production technology
- Added CO2 hydrogenation methanol production technology
- Added a new optimization example with a wind plant and electrolyzer to showcase how to define design variables, constraints, and objective functions
- Added capability for user-defined technologies in the H2Integrate framework, allowing for custom models to be integrated into the system.
- Added an example of a user-defined technology in the `examples` directory, demonstrating an extremely simple paper mill model.
- Added a run of river hydro plant model, an example, and a documentation page.
- Updated the naming scheme throughout the framework so resources produced always have `_out` and resources consumed always have `_in` in their names.
- Removed the `to_organize` directory.
- Split out the electrolyzer cost models `basic` and `singlitico` for clarity.
- Bump min Python version and removed unnecessary packages from `pyproject.toml.
- Moved `overwrite_fin_values` to HOPP
- Enable optimization with HOPP technology ratings using `recreate_hopp_config_for_optimization`
- Added example for running with HOPP as the only technology in the H2Integrate system
- Made caching in the HOPP wrapper optional
- Expanded docs to include a new section on modifying config dicts after model instantiation.
- Added a check for if a custom model's name clashes with an existing model name in the H2Integrate framework, raising an error if it does.
- Refactored the ammonia production model to use the new H2Integrate framework natively and removed the prior performance and cost functions.
- Added a new ammonia production model which has nitrogen, hydrogen, and electricity inputs and ammonia output, with performance and cost functions.
- Added more available constraints from the HOPP wrapper useful for design optimizations
- Added geologic hydrogen (geoh2) converter and examples [PR 135](https://github.com/NREL/H2Integrate/pull/135)
- Added WOMBAT electrolyzer O&M model
- Added marine carbon capture base class
- Added direct ocean capture technology
- Added option for user to provide ProFAST parameters in finance parameters
- Added ammonia synloop, partially addressing https://github.com/NREL/H2Integrate/issues/169
- Added geologic hydrogen (geoh2) converter and examples [PR 135](https://github.com/NREL/H2Integrate/pull/135)
- Changed plant_config `atb_year` entry to `financial_analysis_start_year`
- Allow users to specify the technologies to include in the metrics calculations in the plant configuration file
- Update PySAM solar performance model to allow for more user-configurability.
- Added simple air separation unit (ASU) converter to model nitrogen production.
- Added two ATB-compatible solar-PV cost models.
- Changed electrolyzer capacity to be specified as `n_clusters` rather than `rating` in electrolyzer performance model config
- Changed electrolyzer capacity to be an input to the electrolyzer cost models rather than pulled from the cost model config.
- Updated finance parameter organization naming in `plant_config`.
- Added cost model base class and removed `plant_config['finance_parameters']['discount_years']['tech']`. Some cost models require user-input cost year (`tech_config[tech]['model_inputs']['cost_parameters']['cost_year']`) others do not. Cost year is output from cost models as a discrete output.
- Add ocean alkalinity enhancement technology model.
- Added ability to export ProFAST object to yaml file in `ProFastComp`
- Added `natural_gas_performance` and `natural_gas_cost` models, allowing for natural gas power plant modeling.
- Revamped the feedstocks technology group to allow for more precise modeling of feedstock supply chains, including capacity constraints and feedstock amount consumed.
- Refactored `ProFastComp` and put in a new file (`h2integrate/core/profast_financial.py`). Added flexibility to allow users to specify different financial models.
- Bugfix on `h2integrate/transporters/power_combiner.py` and enabled usage of multiple electricity producing technologies.
- Updated option to pass variables in technology interconnections to allow for different variable names from source to destination in the format `[source_tech, dest_tech, (source_tech_variable, dest_tech_variable)]`
- Added `simulation` section under `plant_config['plant']` that has information such as number of timesteps in the simulation, time step interval in seconds, simulation start time, and time zone.
- Added `"custom_electrolyzer_cost"` model, an electrolyzer cost model that allows for user-defined capex and opex values
- Made `pipe` and `cable` substance-agnostic rather than hard-coded for `hydrogen` and `electricity`
- Change finance handling to use `finance_subgroups` and `finance_groups` defined in the `plant_config` rather than previous `financial_groups` in the `tech_config` and `technologies_to_include_in_metrics` in `plant_config`
- Added variable O&M to `CostModelBaseClass` and integrated into finance-related models
- Added generic storage model, useful for battery, hydrogen, CO2, or other resource storage.
- Added wind resource model, API baseclasses, updated examples, and documentation.
- Added `tools/run_cases.py` with tools to run different `tech_config` cases from a spreadsheet, with new docs page to describe: docs/user_guide/how_to_run_several_cases_in_sequence.md

## 0.3.0 [May 2 2025]

- Introduced a fully new underlying framework for H2Integrate which uses [OpenMDAO](https://openmdao.org/), allowing for more flexibility and extensibility in the future
- Expanded introductory documentation
- Added TOL/MCH hydrogen storage cost model

## 0.2.1, Unreleased, TBD

- Fixed iron data save issue [PR 122](https://github.com/NREL/H2Integrate/pull/122)
- Added optional inputs to electrolyzer model, including curve coefficients and water usage rate.
- Bug-fix in electrolyzer outputs (H2_Results) if some stacks are never turned on.

## 0.2 [7 April 2025]

- Allow users to save the H2IntegrateOutput class as a yaml file and read that yaml to an instance of the output class
- Include new plotting capabilities: (1) hydrogen storage, production, and dispatch; (2) electricity and hydrogen dispatch
- Remove reference_plants from examples. Reference plants can now be found in the [ReferenceHybridSystemDesigns](https://github.com/NREL/ReferenceHybridSystemDesigns) repository.
- Use sentence capitalization for plot labels and legends
- Use "metric ton" instead of "tonne" or "metric tonne" in all internal naming and plots
- Fix bug in hydrogen dispatch plotting by storing time series of hydrogen demand by hour
- Update the PEM efficiency to 51.0 kWh/kg from 54.6 kWh/kg
- Bumped PySAM version to 6+ and HOPP to 3.2.0
- Removed defunct conda build and upload scripts
- Return full solution dictionary from ProFAST, allowing access to CRF and WACC
- Renamed code from GreenHEART to H2Integrate
- Added iron processing framework and capabilities [PR 90](https://github.com/NREL/H2Integrate/pull/90)
- Added Martin and Rosner iron ore models, performance and cost for each [PR 90](https://github.com/NREL/H2Integrate/pull/90)
- Added Rosner direct reduction iron (DRI) model, performance and cost [PR 90](https://github.com/NREL/H2Integrate/pull/90)
- Added Martin transport module for performance and cost of iron [PR 90](https://github.com/NREL/H2Integrate/pull/90)
- Added generalized Stinn cost model for electrolysis of arbitrary materials [PR 90](https://github.com/NREL/H2Integrate/pull/90)

## v0.1.4 [4 February 2025]

- Adds `CoolProp` to `pyproject.toml`
- Changes units of `lcoe_real` in `HOPPComponent` from "MW*h" to "kW*h"
- Adds `pre-commit`, `ruff`, and `isort` checks, and CI workflow to ensure these steps aren't
  skipped.
- Updates steel cost year to 2022
- Updates ammonia cost year to 2022
- Requires HOPP 3.1.1 or higher
- Updates tests to be compatible with HOPP 3.1.1 with ProFAST integration
- Removes support for python 3.9
- Add steel feedstock transport costs (lime, carbon, and iron ore pellets)
- Allow individual debt rate, equity rate, and debt/equity ratio/split for each subsystem
- Add initial docs focused on new H2Integrate development
- New documentation CI pipeline to publish documentation at nrel.github.io/H2Integrate/ and test
  that the documentation site will build on each pull request.
- Placeholder documentation content has been removed from the site build

## v0.1.3 [1 November 2024]

- Replaces the git ProFAST installation with a PyPI installation.
- Removed dependence on external electrolyzer repo
- Updated CI to use conda environments with reproducible environment artifacts
- Rename logger from "wisdem/weis" to "h2integrate"
- Remove unsupported optimization algorithms

## v0.1.2 [28 October 2024]

- Minor updates to examples for NAWEA workshop.
- Adds `environment.yml` for easy environment creation and H2Integrate installation.

## v0.1.1 [22 October 2024]

- ?

## v0.1 [16 October 2024]

- Project has been separated from HOPP and moved into H2Integrate, removing all HOPP infrastructure.
