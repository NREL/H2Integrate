import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class MarineCarbonCapturePerformanceConfig(BaseConfig):
    """Configuration options for marine carbon capture performance modeling.

    Attributes:
        power_single_ed_w (float): Power requirement of a single electrodialysis (ED) unit (watts).
        flow_rate_single_ed_m3s (float): Flow rate of a single ED unit (cubic meters per second).
        number_ed_min (int): Minimum number of ED units to operate.
        number_ed_max (int): Maximum number of ED units available.
        use_storage_tanks (bool): Flag indicating whether to use storage tanks.
        store_hours (float): Number of hours of CO₂ storage capacity (hours).
    """

    power_single_ed_w: float = field()
    flow_rate_single_ed_m3s: float = field()
    number_ed_min: int = field()
    number_ed_max: int = field()
    use_storage_tanks: bool = field()
    store_hours: float = field()


class MarineCarbonCapturePerformanceBaseClass(om.ExplicitComponent):
    """Base OpenMDAO component for modeling marine carbon capture performance.

    This class provides the basic input/output setup and requires subclassing to
    implement actual CO₂ capture calculations.

    Attributes:
        plant_config (dict): Configuration dictionary for plant-level parameters.
        tech_config (dict): Configuration dictionary for technology-specific parameters.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input(
            "electricity_in", val=0.0, shape=8760, units="W", desc="Hourly input electricity (W)"
        )
        self.add_output(
            "co2_capture_rate_mt",
            val=0.0,
            shape=8760,
            units="t",
            desc="Hourly CO₂ capture rate (t)",
        )
        self.add_output("co2_capture_mtpy", units="t/year", desc="Annual CO₂ captured (t/year)")


class MarineCarbonCaptureCostBaseClass(om.ExplicitComponent):
    """Base OpenMDAO component for modeling marine carbon capture costs.

    This class defines the input/output structure for cost evaluation and should
    be subclassed for implementation.

    Attributes:
        plant_config (dict): Configuration dictionary for plant-level parameters.
        tech_config (dict): Configuration dictionary for technology-specific parameters.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input(
            "electricity_in", val=0.0, shape=8760, units="W", desc="Hourly input electricity (W)"
        )
        self.add_input(
            "co2_capture_mtpy",
            val=0.0,
            units="t/year",
            desc="Annual CO₂ captured (t/year)",
        )

        self.add_output("CapEx", val=0.0, units="USD", desc="Total capital expenditure (USD)")
        self.add_output(
            "OpEx",
            val=0.0,
            units="USD/year",
            desc="Total annual operating expenses (USD/year)",
        )

    def compute(self, inputs, outputs):
        """Computes outputs for the marine carbon capture cost model.

        Note:
            This method must be implemented in a subclass.

        Raises:
            NotImplementedError: Always raised unless overridden.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")
