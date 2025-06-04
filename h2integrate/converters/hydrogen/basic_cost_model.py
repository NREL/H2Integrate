from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import gt_zero, contains
from h2integrate.converters.hydrogen.electrolyzer_baseclass import ElectrolyzerCostBaseClass
from h2integrate.simulation.technologies.hydrogen.electrolysis.H2_cost_model import (
    basic_H2_cost_model,
)


@define
class BasicElectrolyzerCostModelConfig(BaseConfig):
    """
    Configuration class for the ECOElectrolyzerPerformanceModel.

    Args:
        rating (float): The rating of the electrolyzer in MW.
        location (str): The location of the electrolyzer; options include "onshore" or "offshore".
        electrolyzer_capex (int): $/kW overnight installed capital costs for a 1 MW system in
            2022 USD/kW (DOE hydrogen program record 24005 Clean Hydrogen Production Cost Scenarios
            with PEM Electrolyzer Technology 05/20/24) #TODO: convert to refs
            (https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/24005-clean-hydrogen-production-cost-pem-electrolyzer.pdf?sfvrsn=8cb10889_1)
    """

    rating: float = field(validator=gt_zero)
    location: str = field(validator=contains(["onshore", "offshore"]))
    electrolyzer_capex: int = field(validator=gt_zero)
    time_between_replacement: int = field(validator=gt_zero)


class BasicElectrolyzerCostModel(ElectrolyzerCostBaseClass):
    """
    An OpenMDAO component that computes the cost of a PEM electrolyzer.
    """

    def setup(self):
        super().setup()
        self.config = BasicElectrolyzerCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

    def compute(self, inputs, outputs):
        # unpack inputs
        plant_config = self.options["plant_config"]

        total_hydrogen_produced = float(inputs["total_hydrogen_produced"])
        electrolyzer_size_mw = self.config.rating
        useful_life = plant_config["plant"]["plant_life"]
        atb_year = plant_config["plant"]["atb_year"]

        # run hydrogen production cost model - from hopp examples
        if self.config.location == "onshore":
            offshore = 0
        else:
            offshore = 1

        (
            electrolyzer_total_capital_cost,
            electrolyzer_OM_cost,
            electrolyzer_capex_kw,
            time_between_replacement,
            h2_tax_credit,
            h2_itc,
        ) = basic_H2_cost_model(
            self.config.electrolyzer_capex,
            self.config.time_between_replacement,
            electrolyzer_size_mw,
            useful_life,
            atb_year,
            inputs["electricity"],
            total_hydrogen_produced,
            0.0,
            0.0,
            include_refurb_in_opex=False,
            offshore=offshore,
        )

        outputs["CapEx"] = electrolyzer_total_capital_cost
        outputs["OpEx"] = electrolyzer_OM_cost
