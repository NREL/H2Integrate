from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import gt_zero
from h2integrate.converters.solar.solar_baseclass import SolarCostBaseClass


@define
class ATBUtilityPVCostModelConfig(BaseConfig):
    capex_per_kWac: float | int = field(validator=gt_zero)
    opex_per_kWac_per_year: float | int = field(validator=gt_zero)


class ATBUtilityPVCostModel(SolarCostBaseClass):
    def setup(self):
        super().setup()
        self.config = ATBUtilityPVCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

        self.add_input("capacity_kWac", val=0.0, units="kW", desc="PV rated capacity in AC")

    def compute(self, inputs, outputs):
        capex = self.config.capex_per_kWac * inputs["capacity_kWac"][0]
        opex = self.config.opex_per_kWac_per_year * inputs["capacity_kWac"][0]
        outputs["CapEx"] = capex
        outputs["OpEx"] = opex
