from attrs import field, define

from h2integrate.core.utilities import CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.validators import gte_zero
from h2integrate.core.model_baseclasses import CostModelBaseClass


@define
class ATBWindPlantCostModelConfig(CostModelBaseConfig):
    capex_per_kW: float | int = field(validator=gte_zero)
    opex_per_kW_per_year: float | int = field(validator=gte_zero)


class ATBWindPlantCostModel(CostModelBaseClass):
    """
    An OpenMDAO component that calculates the capital expenditure (CapEx) for a wind plant.

    Just a placeholder for now, but can be extended with more detailed cost models.
    """

    def setup(self):
        self.config = ATBWindPlantCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()

        self.add_input("total_capacity", val=0.0, units="kW", desc="Wind farm rated capacity in kW")

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        capex = self.config.capex_per_kW * inputs["total_capacity"]
        opex = self.config.opex_per_kW_per_year * inputs["total_capacity"]

        outputs["CapEx"] = capex
        outputs["OpEx"] = opex
