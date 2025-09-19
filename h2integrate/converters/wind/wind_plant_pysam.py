import operator
import functools

import numpy as np
import PySAM.Windpower as Windpower
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.converters.wind.wind_plant_baseclass import WindPerformanceBaseClass


@define
class PYSAMWindPlantPerformanceModelConfig(BaseConfig):
    hub_height: float = field()


class PYSAMWindPlantPerformanceModel(WindPerformanceBaseClass):
    """
    An OpenMDAO component that wraps a WindPlant model.
    It takes wind parameters as input and outputs power generation data.
    """

    def setup(self):
        super().setup()
        self.config = PYSAMWindPlantPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        self.config_name = "WindPowerSingleOwner"
        self.system_model = Windpower.default(self.config_name)

        self.data_to_field_number = {
            "temperature": 1,
            "pressure": 2,
            "wind_speed": 3,
            "wind_direction": 4,
        }

    def format_resource_data(self, hub_height, wind_resource_data):
        """Format wind resource data into the format required for the
        PySAM Windpower module. The data is formatted as:

        - **fields** (*list[int]*): integers corresponding to data type,
            ex: [1, 2, 3, 4, 1, 2, 3, 4]. Ror each field (int) the corresponding data is:
            - 1: Ambient temperature in degrees Celsius
            - 2: Atmospheric pressure in in atmospheres.
            - 3: Wind speed in meters per second (m/s)
            - 4: Wind direction in degrees east of north (degrees).
        - **heights** (*list[int | float]*): floats corresponding to the resource height.
            ex: [100, 100, 100, 100, 120, 120, 120, 120]
        - **data** (*list[list]*): list of length equal to `n_timesteps` with data of
            corresponding field and resource height.
            ex. if `data[t]` is [-23.5, 0.65, 7.6, 261.2, -23.7, 0.65, 7.58, 261.1] then:
            - 23.5 is temperature at 100m at timestep
            - 7.6 is wind speed at 100m at timestep
            - 7.58 is wind speed at 120m at timestep

        Args:
            hub_height (int | float): turbine hub-height in meters.
            wind_resource_data (dict): wind resource data dictionary.

        Returns:
            dict: PySAM formatted wind resource data.
        """

        data_to_precision = {
            "temperature": 1,
            "pressure": 2,
            "wind_speed": 2,
            "wind_direction": 1,
        }
        bounding_heights = self.calculate_bounding_heights_from_resource_data(
            hub_height,
            wind_resource_data,
            resource_vars=["wind_speed", "wind_direction", "temperature"],
        )
        heights = np.repeat(bounding_heights, len(self.data_to_field_number))
        field_number_to_data = {v: k for k, v in self.data_to_field_number.items()}
        fields = np.tile(list(field_number_to_data.keys()), len(bounding_heights))
        n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])
        resource_data = np.zeros((n_timesteps, len(fields)))
        cnt = 0
        for height, field_num in zip(heights, fields):
            rounding_precision = data_to_precision[field_number_to_data[field_num]]
            resource_key = f"{field_number_to_data[field_num]}_{int(height)}m"
            if resource_key in wind_resource_data:
                resource_data[:, cnt] = wind_resource_data[resource_key].round(rounding_precision)
            else:
                if any(
                    field_number_to_data[field_num] in c for c in list(wind_resource_data.keys())
                ):
                    data_heights = [
                        float(c.split("_")[-1].replace("m", "").strip())
                        for c in list(wind_resource_data.keys())
                        if field_number_to_data[field_num] in c
                    ]
                    if len(data_heights) > 1:
                        nearby_heights = [
                            self.calculate_bounding_heights_from_resource_data(
                                hub_ht,
                                wind_resource_data,
                                resource_vars=[field_number_to_data[field_num]],
                            )
                            for hub_ht in data_heights
                        ]
                        nearby_heights = functools.reduce(operator.iadd, nearby_heights, [])
                        nearby_heights = list(set(nearby_heights))
                        if len(nearby_heights) > 1:
                            height_diff = [
                                np.abs(valid_height - height) for valid_height in nearby_heights
                            ]
                            closest_height = nearby_heights[np.argmin(height_diff).flatten()[0]]
                            resource_key = (
                                f"{field_number_to_data[field_num]}_{int(closest_height)}m"
                            )

                        else:
                            resource_key = (
                                f"{field_number_to_data[field_num]}_{int(nearby_heights[0])}m"
                            )

                    else:
                        resource_key = f"{field_number_to_data[field_num]}_{int(data_heights[0])}m"
                    if resource_key in wind_resource_data:
                        resource_data[:, cnt] = wind_resource_data[resource_key].round(
                            rounding_precision
                        )
            cnt += 1
        data = {
            "heights": heights.astype(float).tolist(),
            "fields": fields.tolist(),
            "data": resource_data.tolist(),
        }
        return data

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        data = self.format_resource_data(
            self.config.hub_height, discrete_inputs["wind_resource_data"]
        )
        self.system_model.value("wind_resource_data", data)

        self.system_model.execute(0)
        outputs["electricity_out"] = self.system_model.Outputs.gen
