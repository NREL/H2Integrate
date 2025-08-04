import operator
import functools

import numpy as np
import PySAM.Windpower as Windpower
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import gt_zero, contains
from h2integrate.converters.wind.wind_plant_baseclass import WindPerformanceBaseClass


@define
class PYSAMWindPlantPerformanceModelConfig(BaseConfig):
    """_summary_

    Attributes:
        num_turbines (int): number of turbines in farm
        hub_height (float): wind turbine hub-height in meters
        create_model_from (str):
            - 'default': instatiate Windpower model from the default config 'config_name'
            - 'new': instatiate new Windpower model (default). Requires pysam_options.
        config_name (str,optional): PySAM.Windpower configuration name for non-hybrid wind systems.
            Defaults to 'WindPowerSingleOwner'. Only used if create_model_from='default'.
        pysam_options (dict, optional): dictionary of Windpower input parameters with
            top-level keys corresponding to the different Windpower variable groups.
            (please refer to Windpower documentation
            `here <https://nrel-pysam.readthedocs.io/en/main/modules/Windpower.html>`__
            )
    """

    hub_height: float = field(validator=gt_zero)
    num_turbines: float = field(validator=gt_zero)

    create_model_from: str = field(
        default="new", validator=contains(["default", "new"]), converter=(str.strip, str.lower)
    )

    create_model_from: str = field(
        default="new", validator=contains(["default", "new"]), converter=(str.strip, str.lower)
    )
    config_name: str = field(
        default="WindPowerSingleOwner",
        validator=contains(
            [
                "WindPowerAllEquityPartnershipFlip",
                "WindPowerCommercial",
                "WindPowerLeveragedPartnershipFlip",
                "WindPowerMerchantPlant",
                "WindPowerNone",
                "WindPowerResidential",
                "WindPowerSaleLeaseback",
                "WindPowerSingleOwner",
            ]
        ),
    )
    pysam_options: dict = field(default={})

    def __attrs_post_init__(self):
        if self.create_model_from == "new" and not bool(self.pysam_options):
            msg = (
                "To create a new Windpower object, please provide a dictionary "
                "of Windpower design variables for the 'pysam_options' key."
            )
            raise ValueError(msg)

        self.check_pysam_options()

    def check_pysam_options(self):
        """Checks that top-level keys of pysam_options dictionary are valid and that
        system capacity is not given in pysam_options.

        Raises:
           ValueError: if top-level keys of pysam_options are not valid.
           ValueError: if wind_turbine_hub_ht is provided in pysam_options["Turbine"]
        """
        valid_groups = [
            "Turbine",
            "Farm",
            "Resource",
            "Losses",
            "AdjustmentFactors",
            "HybridCosts",
        ]
        if bool(self.pysam_options):
            invalid_groups = [k for k, v in self.pysam_options.items() if k not in valid_groups]
            if len(invalid_groups) > 0:
                msg = (
                    f"Invalid group(s) found in pysam_options: {invalid_groups}. "
                    f"Valid groups are: {valid_groups}."
                )
                raise ValueError(msg)
            if self.pysam_options.get("Turbine", {}).get("hub_height", None) is not None:
                msg = (
                    "Please do not specify wind_turbine_hub_ht in the pysam_options dictionary. "
                    "The wind turbine hub height should be set with the 'hub_height' "
                    "performance parameter."
                )
                raise ValueError(msg)
        return

    def create_input_dict(self):
        """Create dictionary of inputs to over-write the default values
            associated with the specified Windpower configuration.

        Returns:
           dict: dictionary of Turbine group pararamters from user-input.
        """

        return {"Turbine": {"wind_turbine_hub_ht": self.hub_height}}


@define
class PYSAMWindPlantPerformanceModelSiteConfig(BaseConfig):
    """Configuration class for the location of the wind plant
        PYSAMWindPlantPerformanceComponentSite.

    Attributes:
        latitude (float): Latitude of wind plant location.
        longitude (float): Longitude of wind plant location.
        year (float): Year for resource.
        wind_resource_filepath (str): Path to wind resource file. Defaults to "".
    """

    latitude: float = field()
    longitude: float = field()
    year: float = field()
    elevation: float = field(default=0.0)
    wind_resource_filepath: str = field(default="")


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
        self.site_config = PYSAMWindPlantPerformanceModelSiteConfig.from_dict(
            self.options["plant_config"]["site"], strict=False
        )

        self.add_input(
            "num_turbines",
            val=self.config.num_turbines,
            units="unitless",
            desc="number of turbines in farm",
        )

        self.add_output(
            "wind_turbine_rating",
            val=0.0,
            units="kW",
            desc="rating of an individual turbine in kW",
        )

        self.add_output(
            "annual_energy",
            val=0.0,
            units="kW*h/year",
            desc="Annual energy production from WindPlant in kW",
        )
        self.add_output("capacity_kW", val=0.0, units="kW", desc="Wind farm rated capacity in kW")

        if self.config.create_model_from == "default":
            self.system_model = Windpower.default(self.config.config_name)
        elif self.config.create_model_from == "new":
            self.system_model = Windpower.new(self.config.config_name)

        design_dict = self.config.create_input_dict()
        if bool(self.config.pysam_options):
            for group, group_parameters in self.config.pysam_options.items():
                if group in design_dict:
                    design_dict[group].update(group_parameters)
                else:
                    design_dict.update({group: group_parameters})
        self.system_model.assign(design_dict)

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
        data = self.format_resource_data(
            self.config.hub_height, discrete_inputs["wind_resource_data"]
        )
        self.system_model.value("wind_resource_data", data)

        self.system_model.execute(0)

        outputs["electricity_out"] = self.system_model.Outputs.gen
        outputs["capacity_kW"] = self.system_model.Farm.system_capacity
