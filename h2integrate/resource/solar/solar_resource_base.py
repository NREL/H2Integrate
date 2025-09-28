from openmdao.utils import units

from h2integrate.resource.resource_base import ResourceBaseAPIModel


# @define
# class SolarResourceBaseAPIConfig(ResourceBaseAPIConfig):
#     resource_type: str = "solar"


class SolarResourceBaseAPIModel(ResourceBaseAPIModel):
    def setup(self):
        super().setup()

        self.output_vars_to_units = {
            "wind_direction": "deg",
            "wind_speed": "m/s",
            "temperature": "C",
            "pressure": "mbar",
            # 'precipitation_rate': 'mm/h',
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
            # 'ozone': 'unitless', #unsure
            # 'alpha': 'unitless', #unsure
            # 'asymmetry': 'unitless', #unsure
            # 'cloud_type': 'obj',
            # 'fill_flag': 'obj',
            # 'SSA': '', #unsure,
            # 'Global Horizontal UV Irradiance (280-400nm)': 'W/m**2', #unsure,
            # 'Global Horizontal UV Irradiance (295-385nm)': 'W/m**2', #unsure,
        }

    def compare_units_and_correct(self, data, data_units):
        for data_col, orig_units in data_units.items():
            output_var = [k for k, v in self.output_vars_to_units.items() if data_col == k]
            if len(output_var) == 1:
                desired_units = self.output_vars_to_units[output_var[0]]
                if desired_units != orig_units:
                    data[data_col] = units.convert_units(
                        data[data_col].values, orig_units, desired_units
                    )
                    data_units[data_col] = desired_units
            else:
                if len(output_var) < 1:
                    raise Warning(f"{data_col} not found as common variable.")
                else:
                    raise Warning(f"{output_var} not found as a unique common variable.")
        return data, data_units
