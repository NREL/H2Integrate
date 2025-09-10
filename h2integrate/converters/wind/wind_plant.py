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
