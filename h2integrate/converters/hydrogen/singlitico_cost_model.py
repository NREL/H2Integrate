from attrs import field, define

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.core.model_base import CostModelBaseConfig
from h2integrate.core.validators import contains, must_equal
from h2integrate.converters.hydrogen.electrolyzer_baseclass import ElectrolyzerCostBaseClass
from h2integrate.simulation.technologies.hydrogen.electrolysis.PEM_costs_Singlitico_model import (
    PEMCostsSingliticoModel,
)


@define
class SingliticoCostModelConfig(CostModelBaseConfig):
    """
    Configuration class for the ECOElectrolyzerPerformanceModel, outputs costs in 2021 USD.

    Args:
        location (str): The location of the electrolyzer; options include "onshore" or "offshore".
        electrolyzer_capex (int): $/kW overnight installed capital costs for a 1 MW system in
            2022 USD/kW (DOE hydrogen program record 24005 Clean Hydrogen Production Cost Scenarios
            with PEM Electrolyzer Technology 05/20/24) #TODO: convert to refs
            (https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/24005-clean-hydrogen-production-cost-pem-electrolyzer.pdf?sfvrsn=8cb10889_1)
    """

    location: str = field(validator=contains(["onshore", "offshore"]))
    electrolyzer_capex: int = field()
    cost_year: int = field(default=2021, converter=int, validator=must_equal(2021))


class SingliticoCostModel(ElectrolyzerCostBaseClass):
    """
    An OpenMDAO component that computes the cost of a PEM electrolyzer.
    """

    def setup(self):
        self.config = SingliticoCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

        super().setup()

        self.add_input(
            "electrolyzer_size_mw",
            val=0,
            units="MW",
            desc="Size of the electrolyzer in MW",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        electrolyzer_size_mw = inputs["electrolyzer_size_mw"][0]

        # run hydrogen production cost model - from hopp examples
        if self.config.location == "onshore":
            offshore = 0
        else:
            offshore = 1

        P_elec = electrolyzer_size_mw * 1e-3  # [GW]
        RC_elec = self.config.electrolyzer_capex  # [USD/kW]

        pem_offshore = PEMCostsSingliticoModel(elec_location=offshore)

        (
            electrolyzer_capital_cost_musd,
            electrolyzer_om_cost_musd,
        ) = pem_offshore.run(P_elec, RC_elec)

        electrolyzer_total_capital_cost = (
            electrolyzer_capital_cost_musd * 1e6
        )  # convert from M USD to USD
        electrolyzer_OM_cost = electrolyzer_om_cost_musd * 1e6  # convert from M USD to USD

        outputs["CapEx"] = electrolyzer_total_capital_cost
        outputs["OpEx"] = electrolyzer_OM_cost
