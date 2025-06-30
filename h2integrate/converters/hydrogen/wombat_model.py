from pathlib import Path

import numpy as np
from attrs import field, define
from wombat import Simulation
from wombat.core.library import load_yaml

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.converters.hydrogen.eco_tools_pem_electrolyzer import (
    ECOElectrolyzerPerformanceModel,
    ECOElectrolyzerPerformanceModelConfig,
)


@define
class WOMBATModelConfig(ECOElectrolyzerPerformanceModelConfig):
    library_path: Path = field(
        factory=lambda: Path(__file__).parents[3] / "resource_files" / "wombat_library"
    )


class WOMBATElectrolyzerModel(ECOElectrolyzerPerformanceModel):
    def setup(self):
        super().setup()
        self.config = WOMBATModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        self.add_output("capacity_factor", val=0.0, units=None)
        self.add_output("CapEx", val=0.0, units="USD", desc="Capital expenditure")
        self.add_output("OpEx", val=0.0, units="USD/year", desc="Operational expenditure")
        self.add_output(
            "percent_hydrogen_lost",
            val=0.0,
            units="percent",
            desc="Percent hydrogen lost due to O&M maintenance",
        )
        self.add_output(
            "electrolyzer_availability", val=0.0, units=None, desc="Electrolyzer availability"
        )

    def compute(self, inputs, outputs):
        super().compute(inputs, outputs)

        wombat_config = load_yaml(self.config.library_path, "electrolyzer.yml")
        # add external power here after config is loaded
        sim = Simulation(
            library_path=self.config.library_path,
            config=wombat_config,
            random_seed=314,
        )

        sim.run(delete_logs=True, save_metrics_inputs=False)

        scaling_factor = self.config.rating  # The baseline electrolyzer in WOMBAT is 1MW

        # TODO: handle cases where the project is longer than one year.
        # Do the project and divide by the project lifetime using sim.env.simulation_years

        hydrogen_out = outputs["hydrogen_out"].copy()

        availability = sim.metrics.operations[["ELC1"]].values.flatten()

        # Adjust hydrogen_out by availability
        hydrogen_out_with_availability = outputs["hydrogen_out"] * availability

        # Update outputs["hydrogen_out"] with the available hydrogen
        outputs["hydrogen_out"] = hydrogen_out_with_availability

        # Compute total hydrogen produced (sum over the year)
        outputs["total_hydrogen_produced"] = np.sum(hydrogen_out_with_availability)

        # Compute percent hydrogen lost due to O&M maintenance
        percent_hydrogen_lost = 100 * (
            1 - outputs["total_hydrogen_produced"] / np.sum(hydrogen_out)
        )

        outputs["percent_hydrogen_lost"] = percent_hydrogen_lost

        outputs["CapEx"] = self.config.electrolyzer_capex * self.config.rating * 1e3
        outputs["OpEx"] = sim.metrics.opex("annual").iloc[0, 0] * scaling_factor
        outputs["electrolyzer_availability"] = sim.metrics.time_based_availability(
            "annual", "electrolyzer"
        ).values[0]
        outputs["capacity_factor"] = sim.metrics.capacity_factor(
            which="net", frequency="project", by="electrolyzer"
        ).values[0][0]
