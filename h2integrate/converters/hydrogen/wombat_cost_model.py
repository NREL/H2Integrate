from pathlib import Path

import numpy as np
import wombat
import openmdao.api as om
from attrs import field, define
from wombat import Simulation
from wombat.core.library import load_yaml

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import gt_zero
from h2integrate.converters.hydrogen.electrolyzer_baseclass import ElectrolyzerCostBaseClass


@define
class WOMBATCostModelConfig(BaseConfig):
    """ """

    rating_kw: float = field(validator=gt_zero)
    electrolyzer_capex_per_kw: int = field()


class WOMBATCostModel(ElectrolyzerCostBaseClass):
    """
    An OpenMDAO component that computes the cost of a PEM electrolyzer using WOMBAT.
    """

    def setup(self):
        super().setup()
        self.config = WOMBATCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        self.add_output("capacity_factor", val=0.0, units=None)

    def compute(self, inputs, outputs):
        outputs["CapEx"] = self.config.electrolyzer_capex_per_kw * self.config.rating_kw
        # Get the base path where the wombat package is located
        wombat_base_path = Path(wombat.__file__).resolve().parent
        library_folder = (wombat_base_path / ".." / "tests" / "library").resolve()

        # Seed the random variable for consistently randomized results
        np.random.default_rng(0)

        config = load_yaml(".", "poly_electrolyzer.yml")
        sim = Simulation(
            library_path=library_folder,  # automatically directs to the provided library
            config=config,
        )

        sim.run(delete_logs=True, save_metrics_inputs=False)

        scaling_factor = (
            self.config.rating_kw / 1000.0
        )  # The baseline electrolyzer in WOMBAT is 1MW

        outputs["OpEx"] = sim.metrics.opex("annual").iloc[0, 0] * scaling_factor
        outputs["capacity_factor"] = sim.metrics.capacity_factor(
            which="net", frequency="project", by="electrolyzer"
        ).values[0][0]


if __name__ == "__main__":
    prob = om.Problem()
    prob.model.add_subsystem(
        "wombat_cost_model",
        WOMBATCostModel(
            plant_config={},
            tech_config={
                "model_inputs": {
                    "cost_parameters": {
                        "rating_kw": 1000.0,  # 1 MW electrolyzer
                        "electrolyzer_capex_per_kw": 2000.0,  # USD per kW
                    }
                }
            },
        ),
    )

    prob.setup()

    prob.set_val("wombat_cost_model.electricity_in", np.zeros(8760), units="MW")
    prob.run_model()

    prob.model.list_inputs(units=True)
    prob.model.list_outputs(units=True)
