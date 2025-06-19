import openmdao.api as om
from attrs import field, define


try:
    import mcm
except ImportError:
    mcm = None

from h2integrate.core.utilities import BaseConfig


@define
class MarineCarbonCapturePerformanceConfig(BaseConfig):
    power_single_ed_w: float = field()
    flow_rate_single_ed_m3s: float = field()
    number_ed_min: int = field()
    number_ed_max: int = field()
    use_storage_tanks: bool = field()
    store_hours: float = field()


class MarineCarbonCapturePerformanceBaseClass(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling the performance of a marine carbon capture plant.
    This base class is designed to be extended for specific implementations of
    marine carbon capture performance modeling.
    It requires the `mcm` package, which is not included by default. To install the `mcm` package,
    run the following command:
        pip install git+https://github.com/NREL/MarineCarbonManagement.git
    Attributes:
        plant_config (dict): Configuration dictionary for the plant setup.
        tech_config (dict): Configuration dictionary for the technology setup.
    Raises:
        ImportError: If the `mcm` package is not installed.

    """

    def initialize(self):
        if mcm is None:
            raise ImportError(
                "mcm is not installed. `pip install git+https://github.com/NREL/MarineCarbonManagement.git`."
            )
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("electricity_in", val=0.0, shape=8760, units="W")
        self.add_output(
            "co2_capture_rate_mtph", val=0.0, shape=8760, units="t/h", desc="CO2 capture rate"
        )
        self.add_output(
            "average_co2_capture_mtpy", units="t/year", desc="Average annual CO2 capture"
        )


class MarineCarbonCaptureCostBaseClass(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling the cost of marine carbon capture.
    This base class is designed to be extended for specific implementations
    of marine carbon capture cost modeling.
    It requires the `mcm` package, which is not included by default. To install the `mcm` package,
    run the following command:
        pip install git+https://github.com/NREL/MarineCarbonManagement.git
    Attributes:
        plant_config (dict): Configuration dictionary for the plant setup.
        tech_config (dict): Configuration dictionary for the technology setup.
    Raises:
        ImportError: If the `mcm` package is not installed.
    """

    def initialize(self):
        if mcm is None:
            raise ImportError(
                "mcm is not installed. `pip install git+https://github.com/NREL/MarineCarbonManagement.git`."
            )
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        # Inputs for cost model configuration
        self.add_input(
            "average_co2_capture_mtpy", val=0.0, units="t/year", desc="Average annual CO2 capture"
        )
        self.add_input(
            "max_theoretical_co2_capture_mtpy",
            val=0.0,
            units="t/year",
            desc="Maximum theoretical annual CO2 capture",
        )
        self.add_output("CapEx", val=0.0, units="USD", desc="Total capital expenditures")
        self.add_output("OpEx", val=0.0, units="USD/year", desc="Total fixed operating costs")

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")
