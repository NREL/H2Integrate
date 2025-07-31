from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import gt_zero
from h2integrate.converters.solar.solar_baseclass import SolarCostBaseClass


@define
class ATBResComPVCostModelConfig(BaseConfig):
    capex_per_kWdc: float | int = field(validator=gt_zero)
    opex_per_kWdc_per_year: float | int = field(validator=gt_zero)
    pv_capacity_kWdc: float = field()


class ATBResComPVCostModel(SolarCostBaseClass):
    def setup(self):
        super().setup()
        self.config = ATBResComPVCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        self.add_input(
            "capacity_kWdc",
            val=self.config.pv_capacity_kWdc,
            units="kW",
            desc="PV rated capacity in DC",
        )

    def compute(self, inputs, outputs):
        capacity = inputs["capacity_kWdc"][0]
        capex = self.config.capex_per_kWdc * capacity
        opex = self.config.opex_per_kWdc_per_year * capacity
        outputs["CapEx"] = capex
        outputs["OpEx"] = opex
