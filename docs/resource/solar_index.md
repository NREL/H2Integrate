(solar_resource:models)=
# Solar Resource: Model Overview

- [GOES PSM v4 API](solar_resource:goes_v4_api): these models require an API key for the [NREL developer network](https://developer.nrel.gov/signup/), the available models are:
    - "goes_aggregated_solar_v4_api"
    - "goes_conus_solar_v4_api"
    - "goes_fulldisc_solar_v4_api"
    - "goes_tmy_solar_v4_api"


```{note}
Please refer to the `Setting Environment Variables` doc page for information on setting up an NREL API key if you haven't yet.
```

(solarresource:overview)=
# Solar Resource: Output Data

Solar resource models may output solar resource data, site information, information about the data source, and time information. This information is outputted as a dictionary. The following sections detail the naming convention for the dictionary keys, standardized units, and descriptions of all the output data that may be output from a solar resource model.

- [Solar Resource Data](#primary-data-solar-resource-timeseries)
- [Site Information](#additional-data-site-information)
- [Data Source Information](#additional-data-data-source)
- [Time Profile Information](#additional-data-time-profile)


```{note}
Not all solar resource models will output all the data keys listed below. Please check the documentation for each solar resource model and solar performance model to ensure compatibility.
```

(primary-data-solar-resource-timeseries)=
## Primary Data: Solar Resource Timeseries
The below variables are outputted as arrays, with a length equal to the simulation duration. The naming convention and standardized units of solar resource variables are listed below:
- `solar_direction`: solar direction in degrees (units are 'deg')
- `solar_speed`: solar speed in meters per second (units are 'm/s')
- `temperature`: air temperature in Celsius (units are 'C')
- `pressure`: air pressure in millibar (units are 'mbar')
- `relative_humidity`: relative humidity represented as a percentage (units are 'percent')
- `ghi`: global horizontal irrandiance in W/m2 (units are 'W/m**2')
- `dni`: beam normal irrandiance in W/m2 (units are 'W/m**2')
- `dhi`: diffuse horizontal irrandiance in W/m2 (units are 'W/m**2')
- `clearsky_ghi`: global horizontal irrandiance in clearsky conditions in W/m2 (units are 'W/m**2')
- `clearsky_dni`: beam normal irrandiance in clearsky conditions in W/m2 (units are 'W/m**2')
- `clearsky_dhi`: diffuse horizontal irrandiance in clearsky conditions in W/m2 (units are 'W/m**2')
- `dew_point`:  (units are 'C')
- `surface_albedo`:  (units are 'percent')
- `solar_zenith_angle`: (units are 'deg')
- `snow_depth`: (units are 'cm')
- `precipitable_water`: (units are 'cm')

(additional-data-site-information)=
## Additional Data: Site Information
- `site_id` (int): site id
- `site_tz` (int | float): local timezone for the site
- `site_lat` (float): latitude of the site
- `site_lon` (float): longitude of the site
- `elevation` (float | int): elevation of the site in meters

(additional-data-data-source)=
## Additional Data: Data source
- `data_tz` (int | float): timezone the data is in represented as an hour offset from UTC
- `filepath` (str): filepath where the resource data was loaded from

(additional-data-time-profile)=
## Additional Data: Time profile
Time data may be outputted as arrays to represent the time profile of the resource data. These times should be represented in the timezone of `data_tz` (if outputted).
- `year`: year as 4-digit value (i.e., 2019)
- `month`: month of year (1-12)
- `day`: day of month (1-31)
- `hour`: hour of day from a 24-hour clock (0-23)
- `minute`: minute of hour (0-59)
