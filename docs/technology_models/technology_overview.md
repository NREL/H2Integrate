
# Model Overview
Currently, H2I recognizes four types of models:

- [Resource](#resource)
- [Converter](#converters)
- [Transport](#transport)
- [Storage](#storage)
- [Controllers](#controller)

(resource)=
## Resource
`Resource` models process resource data that is usually passed to a technology model.

| Resource name     | Resource Type  |
| :---------------- | :---------------: |
| `river_resource`  | river resource |

```{note}
The `Resource` models are under development. Many of the resources are currently integrated into the `Converter` model directly, notably this is true for the wind resource used in the `wind` converter and solar resource used in the `solar` converter.
```

(converters)=
## Converters
`Converter` models are technologies that:
- converts energy available in the 'Primary Input' to another form of energy ('Primary Commodity') OR
- consumes the 'Primary Input' (and perhaps secondary inputs or feedstocks), which is converted to the 'Primary Commodity' through some process

The inputs, outputs, and corresponding technology that are currently available in H2I are listed below:

| Technology name   | Primary Commodity | Primary Input(s) |
| :---------------- | :-----------: | ------------: |
| `wind`           |  electricity  | wind resource |
| `solar`          |  electricity  | solar resource |
| `river`          |  electricity  | river resource |
| `hopp`           |  electricity  | N/A |
| `electrolyzer`   |  hydrogen     | electricity |
| `geoh2`          |  hydrogen     | ??? |
| `steel`          |  steel        | hydrogen |
| `ammonia`        |  ammonia      | nitrogen, hydrogen |
| `doc`   |  co2     | electricity |
| `oae`   |  co2     | electricity |
| `methanol`   |  methanol     | ??? |
| `air_separator`   |  nitrogen     | electricity |
| `desal`   |  water     | electricity |

(transport)=
## Transport
`Transport` models are used to either:
- connect the 'Transport Commodity' from a technology that produces the 'Transport Commodity' to a technology that consumes or stores the 'Transport Commodity' OR
- combine multiple input streams of the 'Transport Commodity' into a single stream
- split a single input stream of the 'Transport Commodity' into multiple output streams



| Technology        | Transport Commodity |
| :---------------- | :---------------: |
| `cable`         |  electricity      |
| `pipe`      |  hydrogen         |
| `combiner`      |  Any    |
| `splitter` | electricity |

Connection: `[source_tech, dest_tech, transport_commodity, transport_technology]`

(storage)=
## Storage
`Storage` technologies input and output the 'Storage Commodity' at different times. These technologies can be filled or charged, then unfilled or discharged at some later time. These models are usually constrained by two key model parameters: storage capacity and charge/discharge rate.

| Technology        | Storage Commodity |
| :---------------- | :---------------: |
| `h2_storage`      |  hydrogen         |
| `battery`         |  electricity      |

(controller)=
## Controller
`Controller` models are used to control the `Storage` models and resource flows.

| Controller        | Control Method |
| :----------------------------- | :---------------: |
| `pass_through_controller`      |  open-loop control. directly passes the input resource flow to the output without any modifications         |
| `demand_open_loop_controller`  |  open-loop control. manages resource flow based on demand and storage constraints     |

# Technology Models Overview

Below summarizes the available performance, cost, and financial models for each model type. The list of supported models is also available in [supported_models.py](../../h2integrate/core/supported_models.py)
- [Resource](#resource-models)
- [Converters](#converter-models)
- [Transport](#transport-models)
- [Storage](#storage-models)

(resource-models)=
### Resource models
- `river`:
    - performance models:
        + `river_resource`

(converter-models)=
### Converter models
- `wind`: wind turbine
    - performance models:
        + `'wind_plant_performance'`
        + `'pysam_wind_plant_performance'`
    - cost models:
        + `'wind_plant_cost'`
- `solar`: solar-PV panels
    - performance models:
        + `'pysam_solar_plant_performance'`
    - cost models:
        + `'atb_utility_pv_cost'`
        + `'atb_comm_res_pv_cost'`
- `river`: hydropower
    - performance models:
        + `'run_of_river_hydro_performance'`
    - cost models:
        + `'run_of_river_hydro_cost'`
- `hopp`: hybrid plant
    - combined performance and cost model:
        + `'hopp'`
- `electrolyzer`: hydrogen electrolysis
    - combined performance and cost:
        + `'wombat'`
    - performance models:
        + `'pem_electrolyzer_performance'`
        + `'eco_pem_electrolyzer_performance'`
    - cost models:
        + `'pem_electrolyzer_cost'`
        + `'singlitico_electrolyzer_cost'`
        + `'basic_electrolyzer_cost'`
- `geoh2`: geologic hydrogen
    - performance models:
        + `'natural_geoh2_performance'`
        + `'stimulated_geoh2_performance'`
    - cost models:
        + `'natural_geoh2_cost'`
        + `'stimulated_geoh2_cost'`
    - finance models:
        + `'natural_geoh2'`
        + `'stimulated_geoh2'`
- `steel`: steel production
    - performance models:
        + `'steel_performance'`
    - combined cost and financial models:
        + `'steel_cost'`
- `ammonia`: ammonia synthesis
    - performance models:
        + `'simple_ammonia_performance'`
        + `'synloop_ammonia_performance'`
    - cost models:
        + `'simple_ammonia_cost'`
        + `'synloop_ammonia_cost'`
- `doc`: direct ocean capture
    - performance models:
        + `'direct_ocean_capture_performance'`
    - cost models:
        + `'direct_ocean_capture_cost'`
- `oae`: ocean alkalinity enhancement
    - performance models:
        + `'ocean_alkalinity_enhancement_performance'`
    - cost models:
        + `'ocean_alkalinity_enhancement_cost'`
    - financial models:
        + `'ocean_alkalinity_enhancement_cost_financial'`
- `methanol`: methanol synthesis
    - performance models:
        + `'smr_methanol_plant_performance'`
    - cost models:
        + `'smr_methanol_plant_cost'`
    - financial models:
        + `'methanol_plant_financial'`
- `air_separator`: nitrogen separation from air
    - performance models:
        + `'simple_ASU_performance'`
    - cost models:
        + `'simple_ASU_cost'`
- `desal`: water desalination
    - performance models:
        + `'reverse_osmosis_desalination_performance'`
    - cost models:
        + `'reverse_osmosis_desalination_cost'`

(transport-models)=
### Transport Models
- `cable`
    - performance models:
        + `'cable'`
- `pipe`:
    - performance models:
        + `'pipe'`
- `combiner`:
    - performance models:
        + `'combiner_performance'`

(storage-models)=
### Storage Models
- `h2_storage`: hydrogen storage
    - combined performance and cost
        + `'h2_storage'`
    - performance models:
        + `'hydrogen_tank_performance'`
    - cost models:
        + `'hydrogen_tank_cost'`

### Controller Models
- `pass_through_controller`
- `demand_open_loop_controller`
