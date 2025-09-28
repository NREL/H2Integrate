(solar_resource:goes_v4_api)=
# Solar Resource: GOES Aggregated PSM v4

This resource class downloads solar resource data from [GOES Aggregated PSM v4](https://developer.nrel.gov/docs/solar/nsrdb/nsrdb-GOES-aggregated-v4-0-0-download/)
and requires an NREL API key to use.

This dataset allows for resource data to be downloaded for:
- **resource years** from 1998 to 2024.
- **locations** within the continental United States.
- **time intervals** of 30 and 60 minutes.

## Available Data

| Resource Data     | Included  |
| :---------------- | :---------------: |
| `wind_direction`      | X  |
| `wind_speed`      | X |
| `temperature`      | X |
| `pressure`      |  X |
| `relative_humidity`      | X |
| `ghi`      | X |
| `dhi`      | X |
| `dni`      | X |
| `clearsky_ghi`      | X |
| `clearsky_dhi`      | X |
| `clearsky_dni`      | X |
| `dew_point`      | X |
| `surface_albedo`      | X |
| `solar_zenith_angle`      | X |
| `snow_depth`      | X |
| `precipitable_water`      | X |

| Additional Data     | Included  |
| :---------------- | :---------------: |
| `site_id`      | X  |
| `site_lat`      | X |
| `site_lon`      | X |
| `elevation`      |  X |
| `site_tz`      | X |
| `data_tz`      | X |
| `filepath`      | X |
| `year`      | X |
| `month`      | X |
| `day`      | X |
| `hour`      | X |
| `minute`      | X |
