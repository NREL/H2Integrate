from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import gt_zero, contains
from h2integrate.converters.hydrogen.pem_model.run_h2_PEM import run_h2_PEM
from h2integrate.converters.hydrogen.electrolyzer_baseclass import ElectrolyzerPerformanceBaseClass


def ceildiv(a, b):
    return -(a // -b)


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
        n_clusters (int): number of electrolyzer clusters within the system.
        location (str): The location of the electrolyzer; options include "onshore" or "offshore".
        cluster_rating_MW (float): The rating of the clusters that the electrolyzer is grouped
            into, in MW.
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
    n_clusters: int = field(validator=gt_zero)
    location: str = field(validator=contains(["onshore", "offshore"]))
    cluster_rating_MW: float = field(validator=gt_zero)
    eol_eff_percent_loss: float = field(validator=gt_zero)
    uptime_hours_until_eol: int = field(validator=gt_zero)
    include_degradation_penalty: bool = field()
    turndown_ratio: float = field(validator=gt_zero)
    electrolyzer_capex: int = field()


class ECOElectrolyzerPerformanceModel(ElectrolyzerPerformanceBaseClass):
    """
    An OpenMDAO component that wraps the PEM electrolyzer model.
    Takes electricity input and outputs hydrogen and oxygen generation rates.
    """

    def setup(self):
        super().setup()
        self.config = ECOElectrolyzerPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=False,
        )
        self.add_output("efficiency", val=0.0, desc="Average efficiency of the electrolyzer")
        self.add_output(
            "rated_h2_production_kg_pr_hr",
            val=0.0,
            units="kg/h",
            desc="Rated hydrogen production of system in kg/hour",
        )

        self.add_input(
            "n_clusters",
            val=self.config.n_clusters,
            units="unitless",
            desc="number of electrolyzer clusters in the system",
        )

        self.add_output(
            "electrolyzer_size_mw",
            val=0.0,
            units="MW",
            desc="Size of the electrolyzer in MW",
        )

    def compute(self, inputs, outputs):
        plant_life = self.options["plant_config"]["plant"]["plant_life"]
        electrolyzer_size_mw = inputs["n_clusters"][0] * self.config.cluster_rating_MW
        electrolyzer_capex_kw = self.config.electrolyzer_capex

        hydrogen_production_capacity_required_kgphr = []
        grid_connection_scenario = "off-grid"
        energy_to_electrolyzer_kw = inputs["electricity_in"]

        n_pem_clusters = int(ceildiv(electrolyzer_size_mw, self.config.cluster_rating_MW))

        electrolyzer_actual_capacity_MW = n_pem_clusters * self.config.cluster_rating_MW
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
            electrolyzer_direct_cost_kw=electrolyzer_capex_kw,
            user_defined_pem_param_dictionary=pem_param_dict,
            grid_connection_scenario=grid_connection_scenario,  # if not offgrid, assumes steady h2 demand in kgphr for full year  # noqa: E501
            hydrogen_production_capacity_required_kgphr=hydrogen_production_capacity_required_kgphr,
            debug_mode=False,
            verbose=False,
        )

        # Assuming `h2_results` includes hydrogen and oxygen rates per timestep
        outputs["hydrogen_out"] = H2_Results["Hydrogen Hourly Production [kg/hr]"]
        outputs["total_hydrogen_produced"] = H2_Results["Life: Annual H2 production [kg/year]"]
        outputs["efficiency"] = H2_Results["Sim: Average Efficiency [%-HHV]"]
        outputs["time_until_replacement"] = H2_Results["Time Until Replacement [hrs]"]
        outputs["rated_h2_production_kg_pr_hr"] = H2_Results["Rated BOL: H2 Production [kg/hr]"]
        outputs["electrolyzer_size_mw"] = electrolyzer_actual_capacity_MW
