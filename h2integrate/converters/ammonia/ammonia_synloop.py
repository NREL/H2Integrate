import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs


@define
class AmmoniaSynLoopPerformanceConfig(BaseConfig):
    """
    Configuration inputs for the ammonia synthesis loop performance model.

    Attributes:
        energy_demand (float): The total energy demand of the ammonia synthesis loop
            (in appropriate units, e.g., MJ or kWh).
        nitrogen_conversion_rate (float): The fraction of nitrogen converted to ammonia in
            the synthesis loop (as a decimal).
        hydrogen_conversion_rate (float): The fraction of hydrogen converted to ammonia in
            the synthesis loop (as a decimal).
    """

    energy_demand: float = field()
    nitrogen_conversion_rate: float = field()
    hydrogen_conversion_rate: float = field()


class AmmoniaSynLoopPerformanceModel(om.ExplicitComponent):
    """
    OpenMDAO component modeling the performance of an ammonia synthesis loop.

    This component calculates the hourly ammonia production based on the available
    hydrogen, nitrogen, and electricity inputs, considering the stoichiometric and
    energetic requirements of the synthesis process. It also computes the unused
    hydrogen, nitrogen, and electricity (as heat), as well as the total ammonia
    produced over the modeled period.
    Attributes
    ----------
    config : AmmoniaSynLoopPerformanceConfig
        Configuration object containing model parameters such as energy demand,
        nitrogen conversion rate, and hydrogen conversion rate.
    Inputs
    ------
    hydrogen_in : array [kg/h]
        Hourly hydrogen feed to the synthesis loop.
    nitrogen_in : array [kg/h]
        Hourly nitrogen feed to the synthesis loop.
    electricity_in : array [MW]
        Hourly electricity supplied to the synthesis loop.
    Outputs
    -------
    ammonia_out : array [kg/h]
        Hourly ammonia produced by the synthesis loop.
    nitrogen_out : array [kg/h]
        Hourly unused nitrogen after synthesis.
    hydrogen_out : array [kg/h]
        Hourly unused hydrogen after synthesis.
    heat_out : array [MW]
        Hourly unused electricity (as heat) after synthesis.
    total_ammonia_produced : float [kg/year]
        Total ammonia produced over the modeled period.
    Notes
    -----
    The ammonia production is limited by the most constraining input (hydrogen,
    nitrogen, or electricity) at each timestep. The component assumes perfect
    conversion efficiency up to the limiting reagent or energy input.
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = AmmoniaSynLoopPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        self.add_input(
            "hydrogen_in", val=0.0, shape_by_conn=True, copy_shape="ammonia_out", units="kg/h"
        )
        self.add_input(
            "nitrogen_in", val=0.0, shape_by_conn=True, copy_shape="ammonia_out", units="kg/h"
        )
        self.add_input(
            "electricity_in", val=0.0, shape_by_conn=True, copy_shape="ammonia_out", units="MW"
        )

        self.add_output(
            "ammonia_out", val=0.0, shape_by_conn=True, copy_shape="hydrogen_in", units="kg/h"
        )
        self.add_output(
            "nitrogen_out", val=0.0, shape_by_conn=True, copy_shape="nitrogen_in", units="kg/h"
        )
        self.add_output(
            "hydrogen_out", val=0.0, shape_by_conn=True, copy_shape="hydrogen_in", units="kg/h"
        )
        self.add_output(
            "heat_out", val=0.0, shape_by_conn=True, copy_shape="nitrogen_in", units="MW"
        )
        self.add_output("total_ammonia_produced", val=0.0, units="kg/year")

    def compute(self, inputs, outputs):
        # Get config values
        energy_demand = self.config.energy_demand  # MW per kg NH3
        n2_rate = self.config.nitrogen_conversion_rate  # kg N2 per kg NH3
        h2_rate = self.config.hydrogen_conversion_rate  # kg H2 per kg NH3

        # Inputs (arrays of length 8760)
        h2_in = inputs["hydrogen_in"]
        n2_in = inputs["nitrogen_in"]
        elec_in = inputs["electricity_in"]

        # Calculate max NH3 production for each input
        nh3_from_h2 = h2_in / h2_rate
        nh3_from_n2 = n2_in / n2_rate
        nh3_from_elec = elec_in / energy_demand

        # Limiting NH3 production per hour
        nh3_prod = np.minimum.reduce([nh3_from_h2, nh3_from_n2, nh3_from_elec])

        # Calculate unused inputs
        used_h2 = nh3_prod * h2_rate
        used_n2 = nh3_prod * n2_rate
        used_elec = nh3_prod * energy_demand

        outputs["ammonia_out"] = nh3_prod
        outputs["hydrogen_out"] = h2_in - used_h2
        outputs["nitrogen_out"] = n2_in - used_n2
        outputs["heat_out"] = elec_in - used_elec
        outputs["total_ammonia_produced"] = nh3_prod.sum()

        @define
        class AmmoniaSynLoopCostConfig(BaseConfig):
            """
            Configuration inputs for the ammonia synthesis loop cost model.

            Attributes:
                capex (float): Capital expenditure for the synthesis loop [$].
                rebuild_cost (float): Annualized catalyst replacement or rebuild cost [$ per year].
            """

            capex: float = field()
            rebuild_cost: float = field()

        class AmmoniaSynLoopCostModel(om.ExplicitComponent):
            """
            OpenMDAO component modeling the cost of an ammonia synthesis loop.

            This component outputs the capital expenditure (CapEx) and annual operating
            expenditure (OpEx) associated with the synthesis loop, based on provided
            configuration values.

            Attributes
            ----------
            config : AmmoniaSynLoopCostConfig
                Configuration object containing CapEx and annual rebuild cost.

            Outputs
            -------
            CapEx : float [$]
                Capital expenditure for the synthesis loop.
            OpEx : float [$ per year]
                Annual operating expenditure (catalyst replacement/rebuild).
            Notes
            -----
            This model assumes all OpEx is due to annualized catalyst replacement/rebuild.
            """

            def initialize(self):
                self.options.declare("plant_config", types=dict)
                self.options.declare("tech_config", types=dict)

            def setup(self):
                self.config = AmmoniaSynLoopCostConfig.from_dict(
                    merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
                )

                self.add_output("CapEx", val=0.0, units="USD")
                self.add_output("OpEx", val=0.0, units="USD/year")

            def compute(self, inputs, outputs):
                # Get config values
                outputs["CapEx"] = self.config.capex
                outputs["OpEx"] = self.config.rebuild_cost
