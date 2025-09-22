import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.model_baseclasses import CostModelBaseClass


@define
class GridBuyPerformanceModelConfig(BaseConfig):
    """Configuration for grid electricity buying performance model."""

    electricity_buy_price: float = field(default=0.08)  # $/kWh
    interconnect_limit: float = field(default=1000000.0)  # kW


class GridBuyPerformanceModel(om.ExplicitComponent):
    """
    An OpenMDAO component that models buying electricity from the grid.

    This component handles:
    - Taking in electricity demand
    - Purchasing electricity from grid to meet demand
    - Calculating costs based on buy price
    - Enforcing interconnect limits
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = GridBuyPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        # Inputs
        self.add_input(
            "electricity_demand",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Electricity demand to be met by grid purchases",
        )

        # Outputs
        self.add_output(
            "electricity_out",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Electricity provided from grid purchases",
        )
        self.add_output(
            "electricity_consumed",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Electricity consumed from grid (positive = buying)",
        )

        # Add inputs for electricity pricing and limits
        self.add_input(
            "electricity_buy_price",
            val=self.config.electricity_buy_price,
            shape_by_conn=True,
            units="USD/kWh",
            desc="Price to buy electricity from grid",
        )
        self.add_input(
            "interconnect_limit",
            val=self.config.interconnect_limit,
            units="kW",
            desc="Maximum power that can be purchased from grid",
        )

    def compute(self, inputs, outputs):
        electricity_demand = inputs["electricity_demand"]
        inputs["electricity_buy_price"]
        interconnect_limit = inputs["interconnect_limit"]

        # Amount to buy from grid (limited by interconnect and demand)
        grid_purchase = np.clip(electricity_demand, 0, interconnect_limit)

        # Electricity out is what we can provide from grid purchases
        electricity_out = grid_purchase

        outputs["electricity_out"] = electricity_out
        outputs["electricity_consumed"] = grid_purchase


@define
class GridBuyCostModelConfig(CostModelBaseConfig):
    """Configuration for grid buying cost model."""

    # Grid connections typically have minimal CapEx and OpEx
    # Most costs are operational (electricity purchases) handled in performance model
    connection_capex: float = field(default=0.0)  # USD
    annual_connection_fee: float = field(default=0.0)  # USD/year


class GridBuyCostModel(CostModelBaseClass):
    """
    An OpenMDAO component that computes the cost of grid buying connections.

    For grid buying connections, most costs are operational (electricity purchases)
    which are handled in the performance model via varopex. This cost model handles
    any fixed infrastructure costs.
    """

    def setup(self):
        self.config = GridBuyCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        super().setup()

        # Add inputs needed for VarOpEx calculation
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        self.add_input(
            "electricity_consumed",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Electricity consumed from grid (from performance model)",
        )
        self.add_input(
            "electricity_buy_price",
            val=0.08,
            shape_by_conn=True,
            units="USD/kWh",
            desc="Price to buy electricity from grid",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # Simple cost model - could be made more sophisticated
        # CapEx could scale with interconnect capacity
        electricity_consumed = inputs["electricity_consumed"]
        buy_price = inputs["electricity_buy_price"]

        # Basic connection costs
        outputs["CapEx"] = self.config.connection_capex
        outputs["OpEx"] = self.config.annual_connection_fee

        # Variable operating expenses - positive costs for purchasing
        outputs["VarOpEx"] = np.sum(electricity_consumed * buy_price)
