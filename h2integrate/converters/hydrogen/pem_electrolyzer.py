from attrs import field, define

from h2integrate.core.utilities import BaseConfig, CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.validators import must_equal
from h2integrate.converters.hydrogen.electrolyzer_baseclass import (
    ElectrolyzerCostBaseClass,
    ElectrolyzerPerformanceBaseClass,
)
from h2integrate.simulation.technologies.hydrogen.electrolysis import (
    PEM_H2_LT_electrolyzer_Clusters,
)
from h2integrate.simulation.technologies.hydrogen.electrolysis.PEM_costs_Singlitico_model import (
    PEMCostsSingliticoModel,
)


@define
class ElectrolyzerPerformanceModelConfig(BaseConfig):
    cluster_size_mw: float = field()
    plant_life: int = field()
    eol_eff_percent_loss: float = field()
    uptime_hours_until_eol: int = field()
    include_degradation_penalty: bool = field()
    turndown_ratio: float = field()


class ElectrolyzerPerformanceModel(ElectrolyzerPerformanceBaseClass):
    """
    An OpenMDAO component that wraps the PEM electrolyzer model.
    Takes electricity input and outputs hydrogen and oxygen generation rates.
    """

    def setup(self):
        super().setup()
        self.config = ElectrolyzerPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        self.electrolyzer = PEM_H2_LT_electrolyzer_Clusters(
            self.config.cluster_size_mw,
            self.config.plant_life,
            self.config.eol_eff_percent_loss,
            self.config.uptime_hours_until_eol,
            self.config.include_degradation_penalty,
            self.config.turndown_ratio,
        )
        self.add_input("cluster_size", val=1.0, units="MW")

    def compute(self, inputs, outputs):
        # Run the PEM electrolyzer model using the input power signal
        self.electrolyzer.max_stacks = inputs["cluster_size"]
        h2_results, h2_results_aggregates = self.electrolyzer.run(inputs["electricity_in"])

        # Assuming `h2_results` includes hydrogen and oxygen rates per timestep
        outputs["hydrogen_out"] = h2_results["hydrogen_hourly_production"]
        outputs["total_hydrogen_produced"] = h2_results_aggregates["Total H2 Production [kg]"]


@define
class ElectrolyzeCostModelConfig(CostModelBaseConfig):
    cluster_size_mw: float = field()
    electrolyzer_cost: float = field()
    cost_year: int = field(default=2021, converter=int, validator=must_equal(2021))


class ElectrolyzerCostModel(ElectrolyzerCostBaseClass):
    """
    An OpenMDAO component that computes the cost of a PEM electrolyzer cluster
    using PEMCostsSinglicitoModel which outputs costs in 2021 USD.
    """

    def setup(self):
        self.cost_model = PEMCostsSingliticoModel(elec_location=1)
        # Define inputs: electrolyzer capacity and reference cost
        self.config = ElectrolyzeCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()

        self.add_input(
            "P_elec",
            val=self.config.cluster_size_mw,
            units="MW",
            desc="Nominal capacity of the electrolyzer",
        )
        self.add_input(
            "RC_elec",
            val=self.config.electrolyzer_cost,
            units="MUSD/GW",
            desc="Reference cost of the electrolyzer",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # Call the cost model to compute costs
        P_elec = inputs["P_elec"] * 1.0e-3  # Convert MW to GW
        RC_elec = inputs["RC_elec"]

        cost_model = self.cost_model
        capex, opex = cost_model.run(P_elec, RC_elec)

        outputs["CapEx"] = capex * 1.0e-6  # Convert to MUSD
        outputs["OpEx"] = opex * 1.0e-6  # Convert to MUSD
