from openmdao.utils import units

from h2integrate.resource.resource_base import ResourceBaseAPIModel


class SolarResourceBaseAPIModel(ResourceBaseAPIModel):
    def setup(self):
        super().setup()

        self.output_vars_to_units = {
            "wind_direction": "deg",
            "wind_speed": "m/s",
            "temperature": "C",
            "pressure": "mbar",
            "relative_humidity": "percent",
            "ghi": "W/m**2",
            "dni": "W/m**2",
            "dhi": "W/m**2",
            "clearsky_ghi": "W/m**2",
            "clearsky_dni": "W/m**2",
            "clearsky_dhi": "W/m**2",
            "dew_point": "C",
            "surface_albedo": "percent",
            "solar_zenith_angle": "deg",
            "snow_depth": "cm",
            "precipitable_water": "cm",
        }

    def compare_units_and_correct(self, data, data_units):
        for data_col, orig_units in data_units.items():
            if data_col in self.output_vars_to_units:
                desired_units = self.output_vars_to_units[data_col]
                if desired_units != orig_units:
                    data[data_col] = units.convert_units(data[data_col], orig_units, desired_units)
                    data_units[data_col] = desired_units
        return data, data_units
