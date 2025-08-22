# Summary of Examples
Examples are intended to showcase usage of H2Integrate for a variety of models, optimization problems, or use-cases.
- [Example 1: Steel](#example-1-01onshoresteelmn)
- [Example 2: Ammonia](#example-2-02texasammonia)
- [Example 3: Methanol](#example-3-03methanol)
- [Example 4: Geologic Hydrogen](#example-4-04geoh2)
- [Example 5: Wind/Electrolyzer Optimization](#example-5-05windh2opt)
- [Example 6: Custom Technology](#example-6-06customtech)
- [Example 7: Hydropower](#example-7-07runofriverplant)
- [Example 8: Wind/Electrolyzer](#example-8-08windelectrolyzer)
- [Example 9: Carbon Capture](#example-9-09co2)
- [Example 10: WOMBAT](#example-10-10electrolyzerom)
- [Example 11: HOPP](#example-11-11hybridenergyplant)
- [Example 12: Ammonia Synloop](#example-12-12ammoniasynloop)
- [Example 13: Air Separator](#example-13-13airseparator)
- [Example 14: Hydrogen Storage Dispatch](#example-14-14windhydrogendispatch)

To run an example, first open the terminal and navigate to the H2Integrate root directory and activate your environment:

```bash
cd /path/to/H2Integrate/
conda activate h2integrate
```

Then navigate to the folder containing the run script for the example

```bash
cd examples/01_onshore_steel_mn
```

Finally, run the python script for that example:
```bash
python run_onshore_steel_mn.py
```

```{note}
Some examples do not have python scripts and instead use Jupyter Notebooks and cannot be run through the terminal
```


### Example 1: `01_onshore_steel_mn`
- run script(s):
    - [examples/01_onshore_steel_mn/run_onshore_steel_mn.py](/examples/01_onshore_steel_mn/run_onshore_steel_mn.py)
- highlighted functionality:
    - `technology_interconnections` in `plant_config`: how to connect resources/commodities between technologies and how to connect variables to models.
    - `technologies_included_in_metrics` in `plant_config['finance_parameters']`: how to specify which technologies to include in each financial calculation.
- finance model included: "ProFastComp"
- connection technologies: "cable" and "pipe"
- technologies included:
    - "hopp"
    - electrolyzer
        - performance model: "eco_pem_electrolyzer_performance"
        - cost model: "singlitico_electrolyzer_cost"
    - h2_storage
        - performance model: "h2_storage"
        - cost model: "h2_storage"
        - control strategy: "pass_through_controller"
    - steel:
        - performance model: "steel_performance"
        - cost model: "steel_cost"
        - finance model: coupled with "steel_cost"
- optimization problem: N/A
- test(s) for example: `tests/h2integrate/test_all_examples.py::test_steel_example`

### Example 2: `02_texas_ammonia`
- run script(s):
    - [examples/02_texas_ammonia/run_texas_ammonia_plant.py](/examples/02_texas_ammonia/run_texas_ammonia_plant.py)
- highlighted functionality:
    - save the ProFAST object(s) to a .yaml file in `plant_config['finance_parameters']`
- finance model included: "ProFastComp"
- connection technologies: "cable" and "pipe"
- technologies included:
    - "hopp"
    - electrolyzer
        - performance model: "eco_pem_electrolyzer_performance"
        - cost model: "singlitico_electrolyzer_cost"
    - h2_storage
        - performance model: "h2_storage"
        - cost model: "h2_storage"
        - control strategy: "pass_through_controller"
    - ammonia:
        - performance model: "simple_ammonia_performance"
        - cost model: "simple_ammonia_cost"
- optimization problem: N/A
- test(s) for example: `tests/h2integrate/test_all_examples.py::test_simple_ammonia_example`

### Example 3: `03_methanol`
- run script(s):
    - [examples/03_methanol/co2_hydrogenation/run_co2h_methanol.py](/examples/03_methanol/co2_hydrogenation/run_co2h_methanol.py)
    - [examples/03_methanol/smr/run_smr_methanol.py](/examples/03_methanol/smr/run_smr_methanol.py)
- highlighted functionality: TODO
- finance model included: "ProFastComp"
- connection technologies: "cable" and "pipe"
- technologies included:
    - co2_hydrogenation:
        - "hopp"
        - electrolyzer
            - performance model: "eco_pem_electrolyzer_performance"
            - cost model: "singlitico_electrolyzer_cost"
        - methanol:
            - performance model: "co2h_methanol_plant_performance"
            - cost model: "co2h_methanol_plant_cost"
            - finance model: "co2h_methanol_plant_financial"
    - smr:
        - methanol:
            - performance model: "smr_methanol_plant_performance"
            - cost model: "smr_methanol_plant_cost"
            - finance model: "smr_methanol_plant_financial"
- optimization problem: N/A
- test(s) for example:
    - `tests/h2integrate/test_all_examples.py::test_smr_methanol_example`
    - `tests/h2integrate/test_all_examples.py::test_co2h_methanol_example`


### Example 4: `04_geo_h2`
- run script(s):
    - [examples/04_geo_h2/run_geo_h2.py](/examples/04_geo_h2/run_geo_h2.py)
- highlighted functionality: TODO
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
    - natural:
        - geoh2:
            - performance model: "natural_geoh2_performance"
            - cost model: "natural_geoh2_cost"
            - finance model: "natural_geoh2"
    - simulated:
        - geoh2:
            - performance model: "stimulated_geoh2_performance"
            - cost model: "stimulated_geoh2_cost"
            - finance model: "stimulated_geoh2"
- optimization problem: N/A
- test(s) for example: N/A

### Example 5: `05_wind_h2_opt`
- run script(s):
    - [examples/05_wind_h2_opt/run_wind_electrolyzer.py](/examples/05_wind_h2_opt/run_wind_electrolyzer.py)
- highlighted functionality:
    - how to set-up and run an optimization
- finance model included: "ProFastComp"
- connection technologies: "cable"
- technologies included:
    - wind
        - performance model: "wind_plant_performance"
        - cost model: "wind_plant_cost"
        - resource type: "pysam_wind"
    - electrolyzer
        - performance model: "eco_pem_electrolyzer_performance"
        - cost model: "singlitico_electrolyzer_cost"
- optimization problem: optimize number of electrolyzer clusters with constraint of minimum `total_hydrogen_produced` to minimize LCOH. Uses COBYLA solver.
- test(s) for example: `tests/h2integrate/test_all_examples.py::test_wind_h2_opt_example`

### Example 6: `06_custom_tech`
- run script(s):
    - [examples/06_custom_tech/run_wind_paper.py](/examples/06_custom_tech/run_wind_paper.py)
- highlighted functionality:
    - how to add a custom technology to the system
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
- optimization problem: N/A
- test(s) for example: `tests/h2integrate/test_all_examples.py::test_paper_example`

### Example 7: `07_run_of_river_plant`
- run script(s):
    - [examples/07_run_of_river_plant/run_river.py](/examples/07_run_of_river_plant/run_river.py)
- highlighted functionality: TODO
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
- optimization problem: N/A
- test(s) for example: `tests/h2integrate/test_all_examples.py::test_hydro_example`

### Example 8: `08_wind_electrolyzer`
- run script(s):
    - [examples/08_wind_electrolyzer/run_wind_electrolyzer.py](/examples/08_wind_electrolyzer/run_wind_electrolyzer.py)
- highlighted functionality: TODO
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
- optimization problem: N/A
- test(s) for example: N/A

### Example 9: `09_co2`
- run script(s):
    - [examples/09_co2/direct_ocean_capture/run_wind_wave_doc.py](/examples/09_co2/direct_ocean_capture/run_wind_wave_doc.py)
    - [examples//09_co2/ocean_alkalinity_enhancement/run_wind_wave_oae.py](/examples/09_co2/ocean_alkalinity_enhancement/run_wind_wave_oae.py)
    - [examples/09_co2/ocean_alkalinity_enhancement_financials/run_wind_wave_oae.py](/examples/09_co2/ocean_alkalinity_enhancement_financials/run_wind_wave_oae.py)
- highlighted functionality: TODO
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
- optimization problem: N/A
- test(s) for example:
    - `tests/h2integrate/test_all_examples.py::test_wind_wave_doc_example`
    - `tests/h2integrate/test_all_examples.py::test_wind_wave_oae_example`
    - `tests/h2integrate/test_all_examples.py::test_wind_wave_oae_example_with_financials`

### Example 10: `10_electrolyzer_om`
- run script(s):
    - [examples/10_electrolyzer_om/run_elecrolyzer_om.py](/examples/10_electrolyzer_om/run_elecrolyzer_om.py)
- highlighted functionality: TODO
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
- optimization problem: N/A
- test(s) for example: N/A

### Example 11: `11_hybrid_energy_plant`
- run script(s):
    - [examples/11_hybrid_energy_plant/run_wind_pv_battery.py](/examples/11_hybrid_energy_plant/run_wind_pv_battery.py)
- highlighted functionality: TODO
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
- optimization problem: N/A
- test(s) for example: `tests/h2integrate/test_all_examples.py::test_hybrid_energy_plant_example`

### Example 12: `12_ammonia_synloop`
- run script(s):
    - [examples/12_ammonia_synloop/run_ammonia_synloop.py](/examples/12_ammonia_synloop/run_ammonia_synloop.py)
- highlighted functionality: TODO
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
- optimization problem: N/A
- test(s) for example: `tests/h2integrate/test_all_examples.py::test_ammonia_synloop_example`

### Example 13: `13_air_separator`
- run script(s):
    - [examples/13_air_separator/run_asu.py](/examples/13_air_separator/run_asu.py)
- highlighted functionality: TODO
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
- optimization problem: N/A
- test(s) for example: `tests/h2integrate/test_all_examples.py::test_asu_example`

### Example 14: `14_wind_hydrogen_dispatch`
- run script(s):
    - [examples/14_wind_hydrogen_dispatch/hydrogen_dispatch.ipynb](/examples/14_wind_hydrogen_dispatch/hydrogen_dispatch.ipynb)
- highlighted functionality:
    - hydrogen storage controller
- finance model included: "ProFastComp"
- connection technologies:
- technologies included:
- optimization problem: N/A
- test(s) for example: `tests/h2integrate/test_all_examples.py::test_hydrogen_dispatch_example`


<!--
### Example Template
- run script(s):
- highlighted functionality:
- finance model included:
- connection technologies:
- technologies included:
    - tech
        - performance model:
        - cost model:
        - finance model:
        - resource type:
- optimization problem:
- test(s) for example:  -->
