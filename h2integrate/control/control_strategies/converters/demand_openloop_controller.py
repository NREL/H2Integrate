import numpy as np

from h2integrate.control.control_strategies.demand_openloop_controller import (
    DemandOpenLoopControlBase,
    DemandOpenLoopControlBaseConfig,
)


class DemandOpenLoopConverterController(DemandOpenLoopControlBase):
    def setup(self):
        self.config = DemandOpenLoopControlBaseConfig.from_dict(
            self.options["tech_config"]["model_inputs"]["control_parameters"]
        )
        super().setup()

    def compute(self, inputs, outputs):
        commodity = self.config.commodity_name
        remaining_demand = inputs[f"{commodity}_demand"] - inputs[f"{commodity}_in"]

        # Calculate missed load and curtailed production
        outputs[f"{commodity}_unmet_demand"] = np.where(remaining_demand > 0, remaining_demand, 0)
        outputs[f"{commodity}_unused_commodity"] = np.where(
            remaining_demand < 0, -1 * remaining_demand, 0
        )

        # Calculate actual output based on demand met and curtailment
        outputs[f"{commodity}_out"] = (
            inputs[f"{commodity}_in"] - outputs[f"{commodity}_unused_commodity"]
        )
