import PySAM.Pvwattsv8 as Pvwatts
from attrs import field, define
from hopp.simulation.technologies.resource import SolarResource

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains, range_val
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
    pv_capacity_kWdc: float = field()
    dc_ac_ratio: float = field(default=1.3)
    array_type: int = field(default=2, validator=contains([0, 1, 2, 3, 4]), converter=int)
    azimuth: float = field(default=180, validator=range_val(0, 360))
    bifaciality: float = field(default=0, validator=range_val(0, 1.0))
    gcr: float = field(default=0.3, validator=range_val(0.01, 0.99))
    inv_eff: float = field(default=96, validator=range_val(90, 99.5))
    losses: float = field(default=14.0757, validator=range_val(-5.0, 99.0))
    module_type: int = field(default=0, validator=contains([0, 1, 2]), converter=int)
    rotlim: float = field(default=45.0, validator=range_val(0.0, 270.0))
    tilt: float = field(default=0.0, validator=range_val(0.0, 90.0))
    use_wf_albedo: bool = field(default=False)

    def create_input_dict(self):
        full_dict = self.as_dict()
        non_design_cols = ["pv_capacity_kWdc", "use_wf_albedo"]
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

        self.config_name = "PVWattsSingleOwner"
        self.system_model = Pvwatts.default(self.config_name)

        design_dict = self.design_config.create_input_dict()

        solar_resource = SolarResource(
            lat=self.config.latitude,
            lon=self.config.longitude,
            year=self.config.year,
            filepath=self.config.solar_resource_filepath,
        )

        self.system_model.assign(design_dict)
        self.system_model.value("solar_resource_data", solar_resource.data)

    def compute(self, inputs, outputs):
        self.system_model.value("system_capacity", inputs["capacity_kWdc"][0])

        self.system_model.execute(0)
        outputs["electricity_out"] = self.system_model.Outputs.gen  # kW-dc
        pv_capacity_kWdc = self.system_model.value("system_capacity")
        dc_ac_ratio = self.system_model.value("dc_ac_ratio")
        # outputs["capacity_kWdc"] = pv_capacity_kWdc
        outputs["capacity_kWac"] = pv_capacity_kWdc / dc_ac_ratio
        outputs["annual_energy"] = self.system_model.value("ac_annual")
