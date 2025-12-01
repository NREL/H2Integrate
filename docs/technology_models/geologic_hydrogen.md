# Geologic Hydrogen Models

Within H2Integrate the geologic hydrogen models are divided into subsurface and surface models. (The surface models have not yet been integrated into H2I but keep an eye out!)

The hydrogen well subsurface accounts for everything that's below ground and accounts for things such as drilling, rock type and the hydrogen extracted or produced using this technology.

## Hydrogen Well Subsurface Models
There are two performance models available to model the hydrogen well subsurface one for natural geologic hydrogen and one for stimulated geologic hydrogen.

- [`"simple_natural_geoh2_performance"`](#simple-natural-geoh2-performance): A basic natural geologic hydrogen model for calculating the wellhead gas flow over the well lifetime (`plant_life`) and the specific hydrogen flow from the accumulated gas.

- [`"templeton_serpentinization_geoh2_performance"`](#templeton-serpentinization-geoh2-performance): A stimulated geologic hydrogen model that estimates the hydrogen production from artificially stimulating geologic formations through a process called serpentinization.

- [`"mathur_modified_geoh2_cost"`](#mathur-modified-geoh2-cost): A subsurface cost model that calculates the capital and operating for subsurface well systems in geologic hydrogen production.

(simple-natural-geoh2-performance)=
### Simple Natural GeoH2 Performance

The modeling approach in this performance model is informed by:
- Mathur et al. (Stanford): https://doi.org/10.31223/X5599G
- Gelman et al. (USGS): https://doi.org/10.3133/pp1900

(templeton-serpentinization-geoh2-performance)=
### Templeton Serpentinization GeoH2 Performance

The modeling approach in this performance model is informed by:
- Mathur et al. (Stanford): https://doi.org/10.31223/X5599G
- Templeton et al. (UC Boulder): https://doi.org/10.3389/fgeoc.2024.1366268

(mathur_modified_geoh2_cost)=
### Mathur Modified GeoH2 Cost

The modeling approach in this cost model is based on:
- Mathur et al. (Stanford): https://doi.org/10.31223/X5599G
- NETL Quality Guidelines: https://doi.org/10.2172/1567736
- Drill cost curves are based on an adapted [GETEM model](https://sam.nrel.gov/geothermal.html)
