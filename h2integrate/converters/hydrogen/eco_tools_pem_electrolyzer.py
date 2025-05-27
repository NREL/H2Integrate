from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import gt_zero, contains
from h2integrate.tools.eco.utilities import ceildiv
from h2integrate.converters.hydrogen.electrolyzer_baseclass import (
    ElectrolyzerCostBaseClass,
    ElectrolyzerPerformanceBaseClass,
)
from h2integrate.simulation.technologies.hydrogen.electrolysis.run_h2_PEM import run_h2_PEM
from h2integrate.simulation.technologies.hydrogen.electrolysis.H2_cost_model import (
    basic_H2_cost_model,
)
from h2integrate.simulation.technologies.hydrogen.electrolysis.PEM_costs_Singlitico_model import (
    PEMCostsSingliticoModel,
)


@define
class ECOElectrolyzerPerformanceModelConfig(BaseConfig):
    """
    Configuration class for the ECOElectrolyzerPerformanceModel.

    Args:
        sizing (dict): A dictionary containing the following model sizing parameters:
            - resize_for_enduse (bool): Flag to adjust the electrolyzer based on the enduse.
            - size_for (str): Determines the sizing strategy, either "BOL" (generous), or
                "EOL" (conservative).
            - hydrogen_dmd (#TODO): #TODO
        rating (float): The rating of the electrolyzer in MW.
        location (str): The location of the electrolyzer; options include "onshore" or "offshore".
        cluster_rating_MW (float): The rating of the clusters that the electrolyzer is grouped
            into, in MW.
        pem_control_type (str): The control strategy to be used by the electrolyzer.
        eol_eff_percent_loss (float): End-of-life (EOL) defined as a percent change in efficiency
            from beginning-of-life (BOL).
        uptime_hours_until_eol (int): Number of "on" hours until the electrolyzer reaches EOL.
        include_degradation_penalty (bool): Flag to include degradation of the electrolyzer due to
            operational hours, ramping, and on/off power cycles.
        turndown_ratio (float): The ratio at which the electrolyzer will shut down.
        electrolyzer_capex (int): $/kW overnight installed capital costs for a 1 MW system in
            2022 USD/kW (DOE hydrogen program record 24005 Clean Hydrogen Production Cost Scenarios
            with PEM Electrolyzer Technology 05/20/24) #TODO: convert to refs
            (https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/24005-clean-hydrogen-production-cost-pem-electrolyzer.pdf?sfvrsn=8cb10889_1)
    """

    sizing: dict = field()
    rating: float = field(validator=gt_zero)
    location: str = field(validator=contains(["onshore", "offshore"]))
    cluster_rating_MW: float = field(validator=gt_zero)
    pem_control_type: str = field(validator=contains(["basic"]))
    eol_eff_percent_loss: float = field(validator=gt_zero)
    uptime_hours_until_eol: int = field(validator=gt_zero)
    include_degradation_penalty: bool = field()
    turndown_ratio: float = field(validator=gt_zero)
    electrolyzer_capex: int = field(validator=gt_zero)


class ECOElectrolyzerPerformanceModel(ElectrolyzerPerformanceBaseClass):
    """
    An OpenMDAO component that wraps the PEM electrolyzer model.
    Takes electricity input and outputs hydrogen and oxygen generation rates.
    """

    def setup(self):
        super().setup()
        self.config = ECOElectrolyzerPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        self.add_output("efficiency", val=0.0, desc="Average efficiency of the electrolyzer")
        self.add_output(
            "rated_h2_production_kg_pr_hr",
            val=0.0,
            units="kg/h",
            desc="Rated hydrogen production of system in kg/hour",
        )

        self.add_input(
            "electrolyzer_size_mw",
            val=self.config.rating,
            units="MW",
            desc="Size of the electrolyzer in MW",
        )

    def compute(self, inputs, outputs):
        plant_life = self.options["plant_config"]["plant"]["plant_life"]
        electrolyzer_size_mw = inputs["electrolyzer_size_mw"]
        electrolyzer_capex_kw = self.config.electrolyzer_capex

        # # IF GRID CONNECTED
        # if plant_config["plant"]["grid_connection"]:
        #     # NOTE: if grid-connected, it assumes that hydrogen demand is input and there is not
        #     # multi-cluster control strategies.
        # This capability exists at the cluster level, not at the
        #     # system level.
        #     if config["sizing"]["hydrogen_dmd"] is not None:
        #         grid_connection_scenario = "grid-only"
        #         hydrogen_production_capacity_required_kgphr = config[
        #             "sizing"
        #         ]["hydrogen_dmd"]
        #         energy_to_electrolyzer_kw = []
        #     else:
        #         grid_connection_scenario = "off-grid"
        #         hydrogen_production_capacity_required_kgphr = []
        #         energy_to_electrolyzer_kw = np.ones(8760) * electrolyzer_size_mw * 1e3
        # # IF NOT GRID CONNECTED
        # else:
        hydrogen_production_capacity_required_kgphr = []
        grid_connection_scenario = "off-grid"
        energy_to_electrolyzer_kw = inputs["electricity"]

        n_pem_clusters = int(ceildiv(electrolyzer_size_mw, self.config.cluster_rating_MW))

        ## run using greensteel model
        pem_param_dict = {
            "eol_eff_percent_loss": self.config.eol_eff_percent_loss,
            "uptime_hours_until_eol": self.config.uptime_hours_until_eol,
            "include_degradation_penalty": self.config.include_degradation_penalty,
            "turndown_ratio": self.config.turndown_ratio,
        }

        H2_Results, h2_ts, h2_tot, power_to_electrolyzer_kw = run_h2_PEM(
            electrical_generation_timeseries=energy_to_electrolyzer_kw,
            electrolyzer_size=electrolyzer_size_mw,
            useful_life=plant_life,
            n_pem_clusters=n_pem_clusters,
            pem_control_type=self.config.pem_control_type,
            electrolyzer_direct_cost_kw=electrolyzer_capex_kw,
            user_defined_pem_param_dictionary=pem_param_dict,
            grid_connection_scenario=grid_connection_scenario,  # if not offgrid, assumes steady h2 demand in kgphr for full year  # noqa: E501
            hydrogen_production_capacity_required_kgphr=hydrogen_production_capacity_required_kgphr,
            debug_mode=False,
            verbose=False,
        )

        # Assuming `h2_results` includes hydrogen and oxygen rates per timestep
        outputs["hydrogen"] = H2_Results["Hydrogen Hourly Production [kg/hr]"]
        outputs["total_hydrogen_produced"] = H2_Results["Life: Annual H2 production [kg/year]"]
        outputs["efficiency"] = H2_Results["Sim: Average Efficiency [%-HHV]"]
        outputs["time_until_replacement"] = H2_Results["Time Until Replacement [hrs]"]
        outputs["rated_h2_production_kg_pr_hr"] = H2_Results["Rated BOL: H2 Production [kg/hr]"]


@define
class SingliticoCostModelConfig(BaseConfig):
    """
    Configuration class for the ECOElectrolyzerPerformanceModel.

    Args:
        rating (float): The rating of the electrolyzer in MW.
        location (str): The location of the electrolyzer; options include "onshore" or "offshore".
        electrolyzer_capex (int): $/kW overnight installed capital costs for a 1 MW system in
            2022 USD/kW (DOE hydrogen program record 24005 Clean Hydrogen Production Cost Scenarios
            with PEM Electrolyzer Technology 05/20/24) #TODO: convert to refs
            (https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/24005-clean-hydrogen-production-cost-pem-electrolyzer.pdf?sfvrsn=8cb10889_1)
        cost_model (str): The cost model used for the electrolyzer. Options include "basic", which
            is based on the H2a project and HFTO's program record for PEM electrolysis, and
            "singlitico2021", which uses cost estimates from that paper. #TODO: convert to refs
    """

    rating: float = field(validator=gt_zero)
    location: str = field(validator=contains(["onshore", "offshore"]))
    electrolyzer_capex: int = field(validator=gt_zero)


class SingliticoCostModel(ElectrolyzerCostBaseClass):
    """
    An OpenMDAO component that computes the cost of a PEM electrolyzer.
    """

    def setup(self):
        super().setup()
        self.config = SingliticoCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

    def compute(self, inputs, outputs):
        electrolyzer_size_mw = self.config.rating

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
        cost_model (str): The cost model used for the electrolyzer. Options include "basic", which
            is based on the H2a project and HFTO's program record for PEM electrolysis, and
            "singlitico2021", which uses cost estimates from that paper. #TODO: convert to refs
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
