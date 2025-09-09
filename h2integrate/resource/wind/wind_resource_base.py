from openmdao.utils import units

from h2integrate.resource.resource_base import ResourceBaseAPIModel


# @define
# class WindResourceBaseAPIConfig(ResourceBaseAPIConfig):
#     resource_type: str = "wind"


class WindResourceBaseAPIModel(ResourceBaseAPIModel):
    def setup(self):
        super().setup()

        self.output_vars_to_units = {
            "wind_direction": "deg",
            "wind_speed": "m/s",
            "temperature": "C",
            "pressure": "atm",
            "precipitation_rate": "mm/h",
            "relative_humidity": "percent",
        }

    def compare_units_and_correct(self, data, data_units):
        for data_col, orig_units in data_units.items():
            output_var = [k for k, v in self.output_vars_to_units.items() if k in data_col]
            if len(output_var) == 1:
                desired_units = self.output_vars_to_units[output_var[0]]
                if desired_units != orig_units:
                    data[data_col] = units.convert_units(
                        data[data_col].values, orig_units, desired_units
                    )
                    data_units[data_col] = desired_units
            else:
                if len(output_var) < 1:
                    raise Warning(f"{output_var} not found as common variable.")
                else:
                    raise Warning(f"{output_var} not found as a unique common variable.")
        return data, data_units
