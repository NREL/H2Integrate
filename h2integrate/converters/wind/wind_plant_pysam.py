import PySAM.Windpower as Windpower
from attrs import field, define
from hopp.simulation.technologies.resource import WindResource

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import gt_zero, contains
from h2integrate.converters.wind.wind_plant_baseclass import WindPerformanceBaseClass
from h2integrate.converters.wind.layout.simple_grid_layout import (
    BasicGridLayoutConfig,
    make_basic_grid_turbine_layout,
)


@define
class PYSAMWindPlantPerformanceModelConfig(BaseConfig):
    """_summary_

    Attributes:
        num_turbines (int): number of turbines in farm
        hub_height (float): wind turbine hub-height in meters
        rotor_diameter (float): wind turbine rotor diameter in meters.
        turbine_rating_kW (float): wind turbined rated power in kW
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

    num_turbines: int = field(converter=int, validator=gt_zero)
    hub_height: float = field(validator=gt_zero)
    rotor_diameter: float = field(validator=gt_zero)
    turbine_rating_kW: float = field(validator=gt_zero)

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

    # layout_mode: str = 'basicgrid'
    # layout_params: dict = field(default={})

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

            if (
                self.pysam_options.get("Turbine", {}).get("wind_turbine_rotor_diameter", None)
                is not None
            ):
                msg = (
                    "Please do not specify wind_turbine_rotor_diameter in the pysam_options "
                    "dictionary. The wind turbine rotor diameter should be set with the "
                    "'rotor_diameter' performance parameter."
                )
                raise ValueError(msg)

        return

    def create_input_dict(self):
        """Create dictionary of inputs to over-write the default values
            associated with the specified Windpower configuration.

        Returns:
           dict: dictionary of Turbine group pararamters from user-input.
        """
        design_dict = {
            "Turbine": {
                "wind_turbine_hub_ht": self.hub_height,
                "wind_turbine_rotor_diameter": self.rotor_diameter,
            },
        }

        return design_dict


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

        # initialize layout config
        performance_inputs = self.options["tech_config"]["model_inputs"]["performance_parameters"]
        layout_options = {}
        if "layout" in performance_inputs:
            layout_params = self.options["tech_config"]["model_inputs"][
                "performance_parameters"
            ].pop("layout")
        layout_mode = layout_params.get("layout_mode", "basicgrid")
        layout_options = layout_params.get("layout_options", {})
        if layout_mode == "basicgrid":
            self.layout_config = BasicGridLayoutConfig.from_dict(layout_options)

        # initialize wind turbine config
        self.config = PYSAMWindPlantPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        # initialize site config for resource data
        self.site_config = PYSAMWindPlantPerformanceModelSiteConfig.from_dict(
            self.options["plant_config"]["site"], strict=False
        )

        self.add_input(
            "num_turbines",
            val=self.config.num_turbines,
            units="unitless",
            desc="number of turbines in farm",
        )

        self.add_input(
            "wind_turbine_rating",
            val=self.config.turbine_rating_kW,
            units="kW",
            desc="rating of an individual turbine in kW",
        )

        self.add_input(
            "rotor_diameter",
            val=self.config.rotor_diameter,
            units="m",
            desc="turbine rotor diameter",
        )

        self.add_input(
            "hub_height",
            val=self.config.hub_height,
            units="m",
            desc="turbine hub-height in meters",
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

        lat = self.site_config.latitude
        lon = self.site_config.longitude
        year = self.site_config.year
        resource_filepath = self.site_config.wind_resource_filepath
        hub_height = self.config.hub_height
        wind_resource = WindResource(
            lat, lon, year, wind_turbine_hub_ht=hub_height, filepath=resource_filepath
        )
        self.system_model.value("wind_resource_data", wind_resource.data)

    def recalculate_power_curve(self, rotor_diameter, turbine_rating_kw):
        elevation = 0
        wind_default_max_cp = 0.45
        wind_default_max_tip_speed = 60
        wind_default_max_tip_speed_ratio = 8
        wind_default_cut_in_speed = 4
        wind_default_cut_out_speed = 25
        wind_default_drive_train = 0
        self.system_model.Turbine.calculate_powercurve(
            turbine_rating_kw,
            rotor_diameter,
            elevation,
            wind_default_max_cp,
            wind_default_max_tip_speed,
            wind_default_max_tip_speed_ratio,
            wind_default_cut_in_speed,
            wind_default_cut_out_speed,
            wind_default_drive_train,
        )
        success = False
        if max(self.system_model.value("wind_turbine_powercurve_powerout")) == float(
            turbine_rating_kw
        ):
            success = True
        return success

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        rotor_diameter = inputs["rotor_diameter"][0]
        inputs["hub_height"][0]
        turbine_rating_kw = inputs["wind_turbine_rating"][0]
        n_turbs = inputs["num_turbines"][0]

        self.recalculate_power_curve(rotor_diameter, turbine_rating_kw)

        x_pos, y_pos = make_basic_grid_turbine_layout(
            self.system_model.value("wind_turbine_rotor_diameter"), n_turbs, self.layout_config
        )

        self.system_model.value("wind_farm_xCoordinates", tuple(x_pos))
        self.system_model.value("wind_farm_yCoordinates", tuple(y_pos))

        self.system_model.execute(0)

        outputs["electricity_out"] = self.system_model.Outputs.gen
        outputs["capacity_kW"] = self.system_model.Farm.system_capacity
        outputs["annual_energy"] = self.system_model.Outputs.annual_energy
