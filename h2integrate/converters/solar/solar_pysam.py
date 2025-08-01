import PySAM.Pvwattsv8 as Pvwatts
from attrs import field, define
from hopp.simulation.technologies.resource import SolarResource

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs, check_pysam_input_params
from h2integrate.core.validators import contains, range_val_or_none
from h2integrate.converters.solar.solar_baseclass import SolarPerformanceBaseClass


@define
class PYSAMSolarPlantPerformanceModelSiteConfig(BaseConfig):
    """Configuration class for the location of the solar pv plant
        PYSAMSolarPlantPerformanceComponentSite.

    Attributes:
        latitude (float): Latitude of wind plant location.
        longitude (float): Longitude of wind plant location.
        year (float): Year for resource.
        solar_resource_filepath (str): Path to solar resource file. Defaults to "".
    """

    latitude: float = field()
    longitude: float = field()
    year: float = field()
    solar_resource_filepath: str = field(default="")


@define
class PYSAMSolarPlantPerformanceModelDesignConfig(BaseConfig):
    """Configuration class for design parameters of the solar pv plant
        PYSAMSolarPlantPerformanceModel which uses the Pvwattsv8 module
        available in PySAM. PySAM documentation can be found
        `here <https://nrel-pysam.readthedocs.io/en/main/modules/Pvwattsv8.html#pvwattsv8>`__


    Attributes:
        pv_capacity_kWdc (float): Required, DC system capacity in kW-dc.
        dc_ac_ratio (float | None): Also known as inverter loading ratio, ratio of max DC
            output of PV to max AC output of inverter. If None, then uses the default
            value associated with config_name.
        create_model_from (str):
            - 'default': instatiate Pvwattsv8 model from the default config 'config_name'
            - 'new': instatiate new Pvwattsv8 model (default). Requires pysam_options.
        config_name (str,optional): PySAM.Pvwattsv8 configuration name for non-hybrid PV systems.
            Defaults to 'PVWattsSingleOwner'. Only used if create_model_from='default'.
        tilt (float | None): Panel tilt angle in the range (0.0, 90.0).
            If None, then uses the default value associated with config_name if create_model_from
            is 'default' unless tilt_angle_func is either set to 'lat' or 'lat-func'.
        tilt_angle_func (str):
            - 'none': use value specific in 'tilt' (default).
            - 'lat-func': optimal tilt angle based on the latitude.
            - 'lat': tilt angle equal to the latitude of the solar resource.
        pysam_options (dict, optional): dictionary of Pvwatts input parameters with
            top-level keys corresponding to the different Pvwattsv8 variable groups.
            (please refer to Pvwattsv8 documentation
            `here <https://nrel-pysam.readthedocs.io/en/main/modules/Pvwattsv8.html>`__
            )

    """

    pv_capacity_kWdc: float = field()

    dc_ac_ratio: float = field(
        default=None, validator=range_val_or_none(0.0, 2.0)
    )  # default value depends on config

    create_model_from: str = field(
        default="new", validator=contains(["default", "new"]), converter=(str.strip, str.lower)
    )

    tilt: float = field(default=None, validator=range_val_or_none(0.0, 90.0))

    tilt_angle_func: str = field(
        default="none",
        validator=contains(["none", "lat-func", "lat"]),
        converter=(str.strip, str.lower),
    )

    config_name: str = field(
        default="PVWattsSingleOwner",
        validator=contains(
            [
                "PVWattsCommercial",
                "PVWattsCommunitySolar",
                "PVWattsHostDeveloper",
                "PVWattsMerchantPlant",
                "PVWattsNone",
                "PVWattsResidential",
                "PVWattsSaleLeaseback",
                "PVWattsSingleOwner",
                "PVWattsThirdParty",
                "PVWattsAllEquityPartnershipFlip",
            ]
        ),
    )

    pysam_options: dict = field(default={})

    def __attrs_post_init__(self):
        if self.create_model_from == "new" and not bool(self.pysam_options):
            msg = (
                "To create a new Pvwattsv8 object, please provide a dictionary "
                "of Pvwattsv8 design variables for the 'pysam_options' key."
            )
            raise ValueError(msg)

        self.check_pysam_options()

    def check_pysam_options(self):
        """Checks that top-level keys of pysam_options dictionary are valid and that
        system capacity is not given in pysam_options.

        Raises:
           ValueError: if top-level keys of pysam_options are not valid.
           ValueError: if system_capacity is provided in pysam_options["SystemDesign"]
        """

        valid_groups = [
            "SolarResource",
            "Lifetime",
            "SystemDesign",
            "Shading",
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
            if self.pysam_options.get("SystemDesign", {}).get("system_capacity", None) is not None:
                msg = (
                    "Please do not specify system_capacity in the pysam_options dictionary. "
                    "The solar-PV capacity (in kW-dc) should be set with the 'pv_capacity_kWdc' "
                    "performance parameter."
                )
                raise ValueError(msg)
        return

    def create_input_dict(self):
        """Create dictionary of inputs to over-write the default values
            associated with the specified PVWatts configuration.

        Returns:
           dict: dictionary of SystemDesign and SolarResource pararamters from user-input.
        """

        full_dict = self.as_dict()
        design_cols = ["dc_ac_ratio", "tilt"]
        design_dict = {k: v for k, v in full_dict.items() if k in design_cols and v is not None}
        return {"SystemDesign": design_dict}


class PYSAMSolarPlantPerformanceModel(SolarPerformanceBaseClass):
    """
    An OpenMDAO component that wraps a SolarPlant model.
    It takes solar parameters as input and outputs power generation data.
    """

    def setup(self):
        super().setup()
        self.config = PYSAMSolarPlantPerformanceModelSiteConfig.from_dict(
            self.options["plant_config"]["site"], strict=False
        )
        self.design_config = PYSAMSolarPlantPerformanceModelDesignConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=False,
        )
        self.add_input(
            "capacity_kWdc",
            val=self.design_config.pv_capacity_kWdc,
            units="kW",
            desc="PV rated capacity in DC",
        )
        self.add_output("capacity_kWac", val=0.0, units="kW", desc="PV rated capacity in AC")
        self.add_output(
            "annual_energy",
            val=0.0,
            units="kW*h/year",
            desc="Annual energy production in kWac",
        )

        if self.design_config.create_model_from == "default":
            self.system_model = Pvwatts.default(self.design_config.config_name)
        elif self.design_config.create_model_from == "new":
            self.system_model = Pvwatts.new(self.design_config.config_name)

        design_dict = self.design_config.create_input_dict()
        tilt = self.calc_tilt_angle()
        design_dict["SystemDesign"].update({"tilt": tilt})

        # update design_dict if user provides non-empty design information
        if bool(self.design_config.pysam_options):
            check_pysam_input_params(design_dict, self.design_config.pysam_options)

            for group, group_parameters in self.design_config.pysam_options.items():
                if group in design_dict:
                    design_dict[group].update(group_parameters)
                else:
                    design_dict.update({group: group_parameters})

        self.system_model.assign(design_dict)

        solar_resource = SolarResource(
            lat=self.config.latitude,
            lon=self.config.longitude,
            year=self.config.year,
            filepath=self.config.solar_resource_filepath,
        )

        self.system_model.value("solar_resource_data", solar_resource.data)

    def calc_tilt_angle(self):
        """Calculates the tilt angle of the PV panel based on the tilt
            option described by design_config.tilt_angle_func

        Returns:
            float: tilt angle of the PV panel in degrees.
        """
        if self.design_config.tilt_angle_func == "none":
            if self.design_config.create_model_from == "default":
                if self.design_config.tilt is None:
                    return self.system_model.value("tilt")
                return self.design_config.tilt
            if self.design_config.create_model_from == "new":
                if self.design_config.tilt is None:
                    return self.pysam_options.get("SystemDesign", {}).get("tilt", 0)
                return self.design_config.tilt

        if self.design_config.tilt_angle_func == "lat":
            return self.config.latitude
        if self.design_config.tilt_angle_func == "lat-func":
            if self.config.latitude <= 25:
                return self.config.latitude * 0.87
            if self.config.latitude > 25 and self.config.latitude <= 50:
                return (self.config.latitude * 0.76) + 3.1
            return self.config.latitude

    def compute(self, inputs, outputs):
        self.system_model.value("system_capacity", inputs["capacity_kWdc"][0])

        self.system_model.execute(0)
        outputs["electricity_out"] = self.system_model.Outputs.gen  # kW-dc
        pv_capacity_kWdc = self.system_model.value("system_capacity")
        dc_ac_ratio = self.system_model.value("dc_ac_ratio")
        outputs["capacity_kWac"] = pv_capacity_kWdc / dc_ac_ratio
        outputs["annual_energy"] = self.system_model.value("ac_annual")
