(wind_resource:openmeteo_archive)=
# Open-Meteo Wind

This resource class downloads wind resource data from the [OpenMeteo Archive API](https://open-meteo.com/en/docs/historical-weather-api)

This dataset allows for resource data to be downloaded for:
- **resource years** from 1940 to 2024.
- **locations** across the globe.
- **resource heights** from 10 and 100 meters.
- **time intervals** of 60 minutes.

## Available Data

| Resource Data     | Resource Heights (m)  |
| :---------------- | :---------------: |
| `wind_speed`  | 10, 100 |
| `wind_direction`  | 10, 100 |
| `temperature`  | 2 |
| `pressure`  | 0 |
| `precipitation_rate`  | 0 |

| Additional Data     | Included  |
| :---------------- | :---------------: |
| `site_id`      | X  |
| `site_lat`      | X |
| `site_lon`      | X |
| `elevation`      |  -- |
| `site_tz`      |  --  |
| `data_tz`      | X |
| `filepath`      | X |
| `year`      | X |
| `month`      | X |
| `day`      | X |
| `hour`      | X |
| `minute`      | X |
