import copy
from pathlib import Path

import dill
import numpy as np
from attrs import field, define
from floris import TimeSeries, FlorisModel

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs, make_cache_hash_filename
from h2integrate.core.validators import gt_val, gt_zero, gte_zero
from h2integrate.converters.wind.wind_plant_baseclass import WindPerformanceBaseClass
from h2integrate.converters.wind.layout.simple_grid_layout import (
    BasicGridLayoutConfig,
    make_basic_grid_turbine_layout,
)


@define
class FlorisWindPlantPerformanceConfig(BaseConfig):
    num_turbines: int = field(converter=int, validator=gt_zero)
    floris_wake_config: dict = field()
    floris_turbine_config: dict = field()
    floris_operation_model: str = field(default="cosine-loss")
    hub_height: float = field(default=-1, validator=gt_val(-1))
    layout: dict = field(default={})
    hybrid_turbine_design: bool = field(default=False)
    operational_losses: float = field(default=0.0, validator=gte_zero)
    enable_caching: bool = field(default=True)

    # if using multiple turbines, then need to specify resource reference height
    def __attrs_post_init__(self):
        n_turbine_types = len(self.floris_wake_config.get("farm", {}).get("turbine_type", []))
        n_pos = len(self.floris_wake_config.get("farm", {}).get("layout_x", []))
        if n_turbine_types > 1 and n_turbine_types != n_pos:
            self.hybrid_turbine_design = True

        # use floris_turbines
        if self.hub_height < 0 and not self.hybrid_turbine_design:
            self.hub_height = self.floris_turbine_config.get("hub_height")


class FlorisWindPlantPerformanceModel(WindPerformanceBaseClass):
    """
    An OpenMDAO component that wraps a Floris model.
    It takes wind parameters as input and outputs power generation data.
    """

    def setup(self):
        super().setup()

        performance_inputs = self.options["tech_config"]["model_inputs"]["performance_parameters"]

        # initialize layout config
        layout_options = {}
        if "layout" in performance_inputs:
            layout_params = self.options["tech_config"]["model_inputs"]["performance_parameters"][
                "layout"
            ]
        layout_mode = layout_params.get("layout_mode", "basicgrid")
        layout_options = layout_params.get("layout_options", {})
        if layout_mode == "basicgrid":
            self.layout_config = BasicGridLayoutConfig.from_dict(layout_options)
        self.layout_mode = layout_mode

        # initialize wind turbine config
        self.config = FlorisWindPlantPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        if self.config.hybrid_turbine_design:
            raise NotImplementedError(
                "H2I does not currently support running multiple wind turbines with Floris."
            )

        self.add_input(
            "num_turbines",
            val=self.config.num_turbines,
            units="unitless",
            desc="number of turbines in farm",
        )

        self.add_input(
            "hub_height",
            val=self.config.hub_height,
            units="m",
            desc="turbine hub-height in meters",
        )

        self.add_output(
            "total_electricity_produced",
            val=0.0,
            units="kW*h/year",
            desc="Annual energy production from WindPlant",
        )
        self.add_output(
            "total_capacity", val=0.0, units="kW", desc="Wind farm rated capacity in kW"
        )

        self.add_output(
            "capacity_factor", val=0.0, units="percent", desc="Wind farm capacity factor"
        )

        self.n_timesteps = int(self.options["plant_config"]["plant"]["simulation"]["n_timesteps"])

        power_curve = self.config.floris_turbine_config.get("power_thrust_table").get("power")
        self.wind_turbine_rating_kW = np.max(power_curve)

    def format_resource_data(self, hub_height, wind_resource_data):
        # NOTE: could weight resource data of bounding heights like
        # `weighted_parse_resource_data` method in HOPP
        # constant_resource_data = ["wind_shear","wind_veer","reference_wind_height","air_density"]
        # timeseries_resource_data = ["turbulence_intensity","wind_directions","wind_speeds"]

        bounding_heights = self.calculate_bounding_heights_from_resource_data(
            hub_height, wind_resource_data, resource_vars=["wind_speed", "wind_direction"]
        )
        if len(bounding_heights) == 1:
            resource_height = bounding_heights[0]
        else:
            height_difference = [np.abs(hub_height - b) for b in bounding_heights]
            resource_height = bounding_heights[np.argmin(height_difference).flatten()[0]]

        default_ti = self.config.floris_wake_config.get("flow_field", {}).get(
            "turbulence_intensities", 0.06
        )

        ti = wind_resource_data.get("turbulence_intensity", {}).get(
            f"turbulence_intensity_{resource_height}", default_ti
        )
        if isinstance(ti, (int, float)):
            ti = float(
                ti
            )  # [ti]*len(wind_resource_data[f"wind_direction_{resource_height}m"]) #TODO: update
        elif isinstance(ti, (list, np.ndarray)):
            if len(ti) == 1:
                ti = float(ti[0])
            if len(ti) == 0:
                ti = 0.06
        time_series = TimeSeries(
            wind_directions=wind_resource_data[f"wind_direction_{resource_height}m"],
            wind_speeds=wind_resource_data[f"wind_speed_{resource_height}m"],
            turbulence_intensities=ti,
        )

        return time_series

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # NOTE: could update air density based on elevation if elevation is included
        # in the resource data.
        # would need to duplicate the ``calculate_air_density`` function from HOPP

        # Check if the results for the current configuration are already cached
        if self.config.enable_caching:
            config_dict = self.config.as_dict()
            config_dict.update({"wind_turbine_size_kw": self.wind_turbine_rating_kW})
            cache_filename = make_cache_hash_filename(config_dict, inputs, discrete_inputs)

            if Path(cache_filename).exists():
                # Load the cached results
                cache_path = Path(cache_filename)
                with cache_path.open("rb") as f:
                    cached_data = dill.load(f)
                outputs["electricity_out"] = cached_data["electricity_out"]
                outputs["total_capacity"] = cached_data["total_capacity"]
                outputs["total_electricity_produced"] = cached_data["total_electricity_produced"]
                outputs["capacity_factor"] = cached_data["capacity_factor"]
                return

        # If caching is not enabled or a cache file does not exist, run FLORIS
        n_turbs = int(np.round(inputs["num_turbines"][0]))

        floris_config = copy.deepcopy(self.config.floris_wake_config)
        # make default turbulence intensity

        turbine_design = copy.deepcopy(self.config.floris_turbine_config)

        # turbine_design = floris_config["farm"]["turbine_type"][0]

        # update the turbine hub-height in the floris turbine config
        turbine_design.update({"hub_height": inputs["hub_height"][0]})

        # format resource data and input into model
        time_series = self.format_resource_data(
            inputs["hub_height"][0], discrete_inputs["wind_resource_data"]
        )

        # make layout for number of turbines
        if self.layout_mode == "basicgrid":
            x_pos, y_pos = make_basic_grid_turbine_layout(
                turbine_design.get("rotor_diameter"), n_turbs, self.layout_config
            )

        floris_farm = {"layout_x": x_pos, "layout_y": y_pos, "turbine_type": [turbine_design]}

        floris_config["farm"].update(floris_farm)

        # initialize FLORIS
        self.fi = FlorisModel(floris_config)

        # set the layout and wind data in Floris
        self.fi.set(layout_x=x_pos, layout_y=y_pos, wind_data=time_series)

        # run the model
        self.fi.run()
        # power_turbines = self.fi.get_turbine_powers().reshape(
        #     (n_turbs, self.n_timesteps)
        # ) #W
        power_farm = self.fi.get_farm_power().reshape(self.n_timesteps)  # W

        # Adding losses (excluding turbine and wake losses)
        operational_efficiency = (100 - self.config.operational_losses) / 100
        gen = power_farm * operational_efficiency / 1000  # kW

        outputs["electricity_out"] = gen
        outputs["total_capacity"] = n_turbs * self.wind_turbine_rating_kW

        max_production = n_turbs * self.wind_turbine_rating_kW * len(gen)
        outputs["total_electricity_produced"] = np.sum(gen)
        outputs["capacity_factor"] = np.sum(gen) / max_production

        # Cache the results for future use
        if self.config.enable_caching:
            cache_path = Path(cache_filename)
            with cache_path.open("wb") as f:
                floris_results = {
                    "electricity_out": outputs["electricity_out"],
                    "total_capacity": outputs["total_capacity"],
                    "total_electricity_produced": outputs["total_electricity_produced"],
                    "capacity_factor": outputs["capacity_factor"],
                    "layout_x": x_pos,
                    "layout_y": y_pos,
                }
                dill.dump(floris_results, f)
