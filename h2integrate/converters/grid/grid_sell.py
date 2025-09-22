import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.model_baseclasses import CostModelBaseClass


@define
class GridSellPerformanceModelConfig(BaseConfig):
    """Configuration for grid electricity selling performance model."""

    electricity_sell_price: float = field(default=0.05)  # $/kWh
    interconnect_limit: float = field(default=1000000.0)  # kW


class GridSellPerformanceModel(om.ExplicitComponent):
    """
    An OpenMDAO component that models selling electricity to the grid.

    This component handles:
    - Taking in excess electricity from plant generation
    - Selling excess electricity to grid
    - Calculating revenue based on sell price
    - Enforcing interconnect limits
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = GridSellPerformanceModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        # Inputs
        self.add_input(
            "electricity_in",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Excess electricity available to sell to grid",
        )

        # Add inputs for electricity pricing and limits
        self.add_input(
            "electricity_sell_price",
            val=self.config.electricity_sell_price,
            shape_by_conn=True,
            units="USD/kWh",
            desc="Price to sell electricity to grid",
        )
        self.add_input(
            "interconnect_limit",
            val=self.config.interconnect_limit,
            units="kW",
            desc="Maximum power that can be sold to grid",
        )

        # Outputs
        self.add_output(
            "electricity_consumed",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Electricity sold to grid (negative = selling)",
        )

    def compute(self, inputs, outputs):
        electricity_in = inputs["electricity_in"]
        sell_price = inputs["electricity_sell_price"]
        interconnect_limit = inputs["interconnect_limit"]

        # Amount to sell to grid (limited by interconnect and available electricity)
        # Only sell positive electricity amounts
        grid_sale = np.clip(electricity_in, 0, interconnect_limit)

        # Revenue calculations - negative costs (revenue) for selling
        varopex = -np.sum(grid_sale * sell_price)

        outputs["electricity_consumed"] = -grid_sale  # Negative because we're selling
        outputs["varopex"] = varopex


@define
class GridSellCostModelConfig(CostModelBaseConfig):
    """Configuration for grid selling cost model."""

    # Grid connections typically have minimal CapEx and OpEx
    # Most revenue is operational (electricity sales) handled in performance model
    connection_capex: float = field(default=0.0)  # USD
    annual_connection_fee: float = field(default=0.0)  # USD/year


class GridSellCostModel(CostModelBaseClass):
    """
    An OpenMDAO component that computes the cost of grid selling connections.

    For grid selling connections, most revenue is operational (electricity sales)
    which are handled in the performance model via varopex. This cost model handles
    any fixed infrastructure costs.
    """

    def setup(self):
        self.config = GridSellCostModelConfig.from_dict(
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
            desc="Electricity sold to grid (from performance model, negative values)",
        )
        self.add_input(
            "electricity_sell_price",
            val=0.05,
            shape_by_conn=True,
            units="USD/kWh",
            desc="Price to sell electricity to grid",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # Simple cost model - could be made more sophisticated
        # CapEx could scale with interconnect capacity
        electricity_consumed = inputs["electricity_consumed"]  # Negative values for selling
        sell_price = inputs["electricity_sell_price"]

        # Basic connection costs
        outputs["CapEx"] = self.config.connection_capex

        # Variable operating expenses - negative costs (revenue) for selling
        # electricity_consumed is negative for selling, so multiply by sell_price
        # to get negative cost (revenue)
        outputs["OpEx"] = self.config.annual_connection_fee
        outputs["VarOpEx"] = np.sum(electricity_consumed * sell_price)
