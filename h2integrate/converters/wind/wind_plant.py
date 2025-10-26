import operator
import functools

import numpy as np
from attrs import field, define
from hopp.simulation.technologies.sites import SiteInfo, flatirons_site
from hopp.simulation.technologies.wind.wind_plant import WindPlant

from h2integrate.core.utilities import BaseConfig, CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.model_baseclasses import CostModelBaseClass
from h2integrate.converters.wind.wind_plant_baseclass import WindPerformanceBaseClass


@define
class WindPlantPerformanceModelConfig(BaseConfig):
    num_turbines: int = field()
    turbine_rating_kw: float = field()
    rotor_diameter: float = field()
    hub_height: float = field()
    layout_mode: str = field()
    model_name: str = field()
    model_input_file: str = field()
    layout_params: dict = field()
    rating_range_kw: list = field()
    floris_config: str = field()
    operational_losses: float = field()
    timestep: list = field()
    fin_model: list = field()
    name: str = field()
    turbine_name: str = field()
    turbine_group: str = field()
    override_wind_resource_height: bool = field()
    adjust_air_density_for_elevation: bool = field()


@define
class WindPlantPerformanceModelPlantConfig(BaseConfig):
    plant_life: int = field()


class WindPlantPerformanceModel(WindPerformanceBaseClass):
    """
    An OpenMDAO component that wraps a WindPlant model.
    It takes wind parameters as input and outputs power generation data.
    """

    def setup(self):
        super().setup()
        self.config = WindPlantPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        self.plant_config = WindPlantPerformanceModelPlantConfig.from_dict(
            self.options["plant_config"]["plant"], strict=False
        )

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

        # find the resource heights that are closest to the hub-height for
        # PySAM Windpower resoure data except pressure
        bounding_heights = self.calculate_bounding_heights_from_resource_data(
            hub_height,
            wind_resource_data,
            resource_vars=["wind_speed", "wind_direction", "temperature"],
        )

        # create list of resource heights and fields (as numbers)
        # heights and fields should be the same length
        # heights is a list of resource heights for each data type
        heights = np.repeat(bounding_heights, len(self.data_to_field_number))
        field_number_to_data = {v: k for k, v in self.data_to_field_number.items()}
        # fields is a list of numbers representing the data type
        fields = np.tile(list(field_number_to_data.keys()), len(bounding_heights))
        n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])

        # initialize resource data array
        resource_data = np.zeros((n_timesteps, len(fields)))
        cnt = 0
        for height, field_num in zip(heights, fields):
            # get the rounding precision for the field
            rounding_precision = data_to_precision[field_number_to_data[field_num]]
            # make the keyname for the field number and resource height to
            # pull from the wind_resource_dict
            resource_key = f"{field_number_to_data[field_num]}_{int(height)}m"
            if resource_key in wind_resource_data:
                # the resource data exists!
                resource_data[:, cnt] = wind_resource_data[resource_key].round(rounding_precision)
            else:
                # see if the wind resource data includes any data for the field variable
                if any(
                    field_number_to_data[field_num] in c for c in list(wind_resource_data.keys())
                ):
                    # get the resource heights for the field variable from wind_resource_data
                    data_heights = [
                        float(c.split("_")[-1].replace("m", "").strip())
                        for c in list(wind_resource_data.keys())
                        if field_number_to_data[field_num] in c
                    ]
                    if len(data_heights) > 1:
                        # get the nearest resource heights nearest to the wind turbine hub-height
                        # for all the available resource heights corresponding to the field variable
                        nearby_heights = [
                            self.calculate_bounding_heights_from_resource_data(
                                hub_ht,
                                wind_resource_data,
                                resource_vars=[field_number_to_data[field_num]],
                            )
                            for hub_ht in data_heights
                        ]
                        # make nearby_heights a list of unique values
                        nearby_heights = functools.reduce(operator.iadd, nearby_heights, [])
                        nearby_heights = list(set(nearby_heights))
                        # if theres multiple nearby heights, find the one that is closest
                        # to the target resource height
                        if len(nearby_heights) > 1:
                            height_diff = [
                                np.abs(valid_height - height) for valid_height in nearby_heights
                            ]
                            closest_height = nearby_heights[np.argmin(height_diff).flatten()[0]]
                            # make the resource key for the field and closest height to use
                            resource_key = (
                                f"{field_number_to_data[field_num]}_{int(closest_height)}m"
                            )

                        else:
                            # make the resource key for the field and closest height to use
                            resource_key = (
                                f"{field_number_to_data[field_num]}_{int(nearby_heights[0])}m"
                            )

                    else:
                        # theres only one resource height for the data variable
                        # make the resource key for the field and closest height to use
                        resource_key = f"{field_number_to_data[field_num]}_{int(data_heights[0])}m"
                    if resource_key in wind_resource_data:
                        # check if new key is in wind_resource_data and add the data if it is
                        resource_data[:, cnt] = wind_resource_data[resource_key].round(
                            rounding_precision
                        )
            cnt += 1
        # format data for compatibility with PySAM WindPower
        data = {
            "heights": heights.astype(float).tolist(),
            "fields": fields.tolist(),
            "data": resource_data.tolist(),
        }
        return data

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        resource_data = self.format_resource_data(
            self.config.hub_height, discrete_inputs["wind_resource_data"]
        )
        boundaries = flatirons_site["site_boundaries"]["verts"]
        site_data = {
            "lat": discrete_inputs["wind_resource_data"].get("site_lat", 35.2018863),
            "lon": discrete_inputs["wind_resource_data"].get("site_lon", -101.945027),
            "tz": discrete_inputs["wind_resource_data"].get("site_tz", -6),
            "elev": discrete_inputs["wind_resource_data"].get("elevation", 1099),
            "wind_year": 2012,
            "site_boundaries": {"verts": boundaries},
        }
        site_info = {
            "data": site_data,
            "hub_height": self.config.hub_height,
            "wind_resource": resource_data,
            "solar": False,
            "wind": True,
        }

        self.site = SiteInfo.from_dict(site_info)
        self.wind_plant = WindPlant(self.site, self.config)
        # Assumes the WindPlant instance has a method to simulate and return power output
        self.wind_plant.simulate_power(self.plant_config.plant_life)
        outputs["electricity_out"] = self.wind_plant._system_model.value("gen")


@define
class WindPlantCostModelConfig(CostModelBaseConfig):
    num_turbines: int = field()
    turbine_rating_kw: float = field()
    cost_per_kw: float = field()


class WindPlantCostModel(CostModelBaseClass):
    """
    An OpenMDAO component that calculates the capital expenditure (CapEx) for a wind plant.

    Just a placeholder for now, but can be extended with more detailed cost models.
    """

    def setup(self):
        self.config = WindPlantCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        num_turbines = self.config.num_turbines
        turbine_rating_kw = self.config.turbine_rating_kw
        cost_per_kw = self.config.cost_per_kw

        # Calculate CapEx
        total_capacity_kw = num_turbines * turbine_rating_kw
        outputs["CapEx"] = total_capacity_kw * cost_per_kw
        outputs["OpEx"] = 0.03 * total_capacity_kw * cost_per_kw  # placeholder scalar value
