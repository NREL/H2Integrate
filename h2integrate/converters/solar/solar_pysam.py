import PySAM.Pvwattsv8 as Pvwatts
from attrs import field, define
from hopp.simulation.technologies.resource import SolarResource

from h2integrate.core.utilities import BaseConfig
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
        self.config_name = "PVWattsSingleOwner"
        self.system_model = Pvwatts.default(self.config_name)

        solar_resource = SolarResource(
            lat=self.config.latitude,
            lon=self.config.longitude,
            year=self.config.year,
            filepath=self.config.solar_resource_filepath,
        )

        self.system_model.value("solar_resource_data", solar_resource.data)

    def compute(self, inputs, outputs):
        self.system_model.execute(0)
        outputs["electricity_out"] = self.system_model.Outputs.gen
