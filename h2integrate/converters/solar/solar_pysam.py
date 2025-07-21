import PySAM.Pvwattsv8 as Pvwatts
from attrs import field, define
from hopp.simulation.technologies.resource import SolarResource

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains, range_val, range_val_or_none
from h2integrate.converters.solar.solar_baseclass import SolarPerformanceBaseClass


@define
class PYSAMSolarPlantPerformanceModelSiteConfig(BaseConfig):
    """Configuration class for the location of the solar pv plant
        PYSAMSolarPlantPerformanceComponentSite.

    Args:
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
        PYSAMSolarPlantPerformanceModel. Default values are based on the default
        PVWattsSingleOwner.SystemDesign configuration. PySAM documentation can be found here:
        https://nrel-pysam.readthedocs.io/en/main/modules/Pvwattsv8.html#systemdesign-group


    Args:
        pv_capacity_kWdc (float): Required, DC system capacity in kW-dc.
        dc_ac_ratio (float | None): Also known as inverter loading ratio, ratio of max DC
            output of PV to max AC output of inverter. If None, then uses the default
            value associated with config_name.
        array_type (int | None):
            - None: use default value associated with config_name.
            - 0: fixed open rack
            - 1: fixed roof mount
            - 2: 1-axis tracking
            - 3: 1-axis backtracking
            - 4: 2-axis tracking
        azimuth (float): Angle that the bottom of the panels (parallel to the ground) are tilted at.
            E=90,S=180,W=270,N=360 or 0. Defaults to 180 (south facing).
        bifaciality (float): bifaciliaty factor of the panel in the range (0, 0.85).
            Defaults to 0.0.
        gcr (float): ground coverage ratio in the range (0.01, 0.99). Defaults to 0.0
        inv_eff (float): Inverter efficiency in percent in the range (90, 99.5).
            Linear power conversion loss from DC to AC. Defaults to 96.
        losses (float): DC power losses as a percent. Defaults to 14.0757.
        module_type (int):
            - 0: standard, approximate efficiency of 19%
            - 1: premium, approximate efficiency of 21%
            - 2: thin film, approximate efficiency of 18%
        rotlim (float): rotational limit of panel in degrees (if tracking array type)
            in the range (0.0, 270.0). Defaults to 45.
        tilt (float | None): Panel tilt angle in the range (0.0, 90.0).
            If None, then uses the default value associated with config_name
            unless tilt_angle_func is either set to 'lat' or 'lat-func'.
        use_wf_albedo (bool): if True, use albedo from weather file (if valid).
            If False, use albedo input. Defaults to True.
        config_name (str): PySAM.Pvwattsv8 configuration name for non-hybrid PV systems.
            Defaults to 'PVWattsSingleOwner'.
        tilt_angle_func (str):
            - 'none': use value specific in 'tilt'.
            - 'lat-func': optimal tilt angle based on the latitude.
            - 'lat': tilt angle equal to the latitude of the solar resource.
        create_model_from (str):
            - 'default': instatiate Pvwattsv8 model from the default config 'config_name'
            - 'new': instatiate new Pvwattsv8 model.
        pysam_options (dict, optional): dictionary of Pvwatts input parameters with
            top-level keys corresponding to the different Pvwattsv8 variable groups.
            (please refer to Pvwattsv8 documentation here:
            https://nrel-pysam.readthedocs.io/en/main/modules/Pvwattsv8.html)

    """

    pv_capacity_kWdc: float = field()
    dc_ac_ratio: float = field(
        default=None, validator=range_val_or_none(0.0, 2.0)
    )  # default value depends on config
    array_type: int = field(
        default=None, validator=contains([None, 0, 1, 2, 3, 4])
    )  # default value depends on config
    azimuth: float = field(default=180, validator=range_val(0, 360))
    bifaciality: float = field(default=0, validator=range_val(0, 0.85))
    gcr: float = field(default=0.3, validator=range_val(0.01, 0.99))
    inv_eff: float = field(default=96, validator=range_val(90, 99.5))
    losses: float = field(default=14.0757, validator=range_val(-5.0, 99.0))
    module_type: int = field(default=0, validator=contains([0, 1, 2]), converter=int)
    rotlim: float = field(default=45.0, validator=range_val(0.0, 270.0))
    tilt: float = field(
        default=None, validator=range_val_or_none(0.0, 90.0)
    )  # default value depends on config
    use_wf_albedo: bool = field(default=True)
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
    tilt_angle_func: str = field(
        default="none",
        validator=contains(["none", "lat-func", "lat"]),
        converter=(str.strip, str.lower),
    )
    create_model_from: str = field(
        default="default", validator=contains(["default", "new"]), converter=(str.strip, str.lower)
    )
    pysam_options: dict = field(default={})

    def __attrs_post_init__(self):
        if self.create_model_from == "new" and not bool(self.pysam_options):
            msg = (
                "To create a new PvWattsv8 object, please provide a dictionary "
                "of Pvwattsv8 design variables for the 'pysam_options' key."
            )
            raise ValueError(msg)

    def create_input_dict(self):
        """Create dictionary of inputs to over-write the default values
            associated with the specified PVWatts configuration.

        Returns:
           dict: dictionary of SystemDesign and SolarResource pararamters from user-input.
        """

        full_dict = self.as_dict()
        non_design_cols = [
            "pv_capacity_kWdc",
            "use_wf_albedo",
            "tilt_angle_func",
            "config_name",
            "pysam_options",
            "create_model_from",
        ]
        design_dict = {k: v for k, v in full_dict.items() if k not in non_design_cols}
        return {"SystemDesign": design_dict, "SolarResource": {"use_wf_albedo": self.use_wf_albedo}}


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
            desc="Annual energy production from PVPlant in kWac",
        )

        self.system_model = Pvwatts.default(self.design_config.config_name)

        design_dict = self.design_config.create_input_dict()
        tilt = self.calc_tilt_angle()
        design_dict["SystemDesign"].update({"tilt": tilt})

        # update design_dict if user provides non-empty design information
        if bool(self.design_config.pysam_options):
            design_dict.update(self.design_config.pysam_options)

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
            return self.system_model.value("tilt")
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
