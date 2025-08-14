import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class CostModelBaseConfig(BaseConfig):
    cost_year: int = field(converter=int)


class CostModelBaseClass(om.ExplicitComponent):
    """Baseclass to be used for all cost models. The built-in outputs
    are used by the finance model and must be

    Outputs:
        - CapEx (float): capital expenditure costs in $
        - OpEx (float): annual operating expenditure costs in $/year

    Discrete Outputs:
        - cost_year (int): dollar-year corresponding to CapEx and OpEx values.
            This may be inherent to the cost model, or may depend on user provided input values.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        # Define outputs: CapEx and OpEx costs
        self.add_output("CapEx", val=0.0, units="USD", desc="Capital expenditure")
        self.add_output("OpEx", val=0.0, units="USD/year", desc="Operational expenditure")
        # Define discrete outputs: cost_year
        self.add_discrete_output(
            "cost_year", val=self.config.cost_year, desc="Dollar year for costs"
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")
