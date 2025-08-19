import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.model_baseclasses import CostModelBaseClass


@define
class FeedstockCostConfig(CostModelBaseConfig):
    """Config class for feedstock.

    Attributes:
        name (str): feedstock name
        units (str): feedstock usage units (such as "galUS" or "kg")
        cost (scalar or list):  The cost of the feedstock in USD/`units`).
            If scalar, cost is assumed to be constant for each timestep and each year.
            If list, then it can be the cost per timestep of the simulation
            or per year of the plant life.

        annual_cost (float, optional): fixed cost associated with the feedstock in USD/year
        start_up_cost (float, optional): one-time capital cost associated with the feedstock in USD.
        cost_year (int): dollar-year for costs.
    """

    name: str = field()
    units: str = field()
    cost: int | float | list = field()
    annual_cost: float = field(default=0)
    start_up_cost: float = field(default=0)


class FeedstockCostModel(CostModelBaseClass):
    def initialize(self):
        super().initialize()
        self.options.declare("feedstock_name", types=str)
        return

    def setup(self):
        self.config = FeedstockCostConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )
        self.n_timesteps = n_timesteps = self.options["plant_config"]["plant"]["simulation"][
            "n_timesteps"
        ]

        super().setup()

        self.add_input(
            f"{self.config.name}_consumed",
            val=0.0,
            shape=n_timesteps,
            units=self.config.units,
            desc=f"Consumption profile of {self.config.name}",
        )

        self.add_input(
            f"total_{self.config.name}_consumed",
            val=0.0,
            shape=self.plant_life,
            units=f"{self.config.units}/yr",
            desc=f"Annual consumption of {self.config.name}",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        has_annual_consumption = True
        has_timestep_consumption = True
        if all(c == 0.0 for c in inputs[f"total_{self.config.name}_consumed"]):
            has_annual_consumption = False
        if all(c == 0.0 for c in inputs[f"{self.config.name}_consumed"]):
            has_timestep_consumption = False

        if self.config.start_up_cost > 0:
            outputs["CapEx"] = self.config.start_up_cost
        if self.config.annual_cost > 0:
            outputs["OpEx"] = self.config.annual_cost

        cost_per_year = None
        if isinstance(self.config.cost, list):
            if len(self.config.cost) == self.plant_life and has_annual_consumption:
                annual_consumption = inputs[f"total_{self.config.name}_consumed"]
                cost_per_year = [
                    cost * cons for cost, cons in zip(self.config.cost, annual_consumption)
                ]
                outputs["VarOpEx"] = cost_per_year
                return
            elif len(self.config.cost) == self.n_timesteps and has_timestep_consumption:
                hourly_consumption = inputs[f"{self.config.name}_consumed"]
                cost_per_year = sum(
                    [cost * cons for cost, cons in zip(self.config.cost, hourly_consumption)]
                )
                outputs["VarOpEx"] = [cost_per_year] * self.plant_life
                return
            else:
                msg = "Missing input or incorrect length of cost input"
                if len(self.config.cost) == self.plant_life:
                    msg = (
                        f"Cost of {self.config.name} provided on annual basis ({self.plant_life} "
                        f"entries) but annual consumption was not input"
                        f"(`total_{self.config.name}_consumed` has values of zero)"
                    )
                if len(self.config.cost) == self.n_timesteps:
                    msg = (
                        f"Cost of {self.config.name} provided per time-step ({self.n_timesteps} "
                        f"entries) but hourly consumption was not input"
                        f" (`{self.config.name}_consumed` has values of zero)"
                    )
                if (
                    len(self.config.cost) != self.plant_life
                    and len(self.config.cost) != self.n_timesteps
                ):
                    msg = (
                        f"Costs provided for {self.config.name} must either have a length of "
                        f"{self.plant_life} or {self.n_timesteps}, but list of costs has length "
                        f"of {len(self.config.cost)}."
                    )
                raise ValueError(msg)
        else:
            if has_annual_consumption:
                cost_per_year = [
                    self.config.cost * c for c in inputs[f"total_{self.config.name}_consumed"]
                ]
                outputs["VarOpEx"] = cost_per_year
                return
            if has_timestep_consumption:
                cost_per_year = [
                    sum(inputs[f"{self.config.name}_consumed"]) * self.config.cost
                ] * self.plant_life
                outputs["VarOpEx"] = cost_per_year
                return


class FeedstockComponent(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("feedstocks_config", types=dict)

    def setup(self):
        self.feedstock_data = {}
        for feedstock_name, feedstock_data in self.options["feedstocks_config"].items():
            self.feedstock_data[feedstock_name] = feedstock_data
            self.add_output(feedstock_name, shape=(8760,), units=feedstock_data["capacity_units"])
            self.add_output(f"{feedstock_name}_CapEx", val=0.0, units="USD")
            self.add_output(f"{feedstock_name}_OpEx", val=0.0, units="USD/yr")

        # Add total CapEx and OpEx outputs
        self.add_output("CapEx", val=0.0, units="USD")
        self.add_output("OpEx", val=0.0, units="USD/yr")

    def compute(self, inputs, outputs):
        total_capex = 0.0
        total_opex = 0.0

        for feedstock_name, feedstock_data in self.feedstock_data.items():
            rated_capacity = feedstock_data["rated_capacity"]
            price = feedstock_data["price"]

            # Generate feedstock array operating at full capacity for the full year
            outputs[feedstock_name] = np.full(8760, rated_capacity)

            # Calculate capex (given as $0)
            capex = 0.0
            outputs[f"{feedstock_name}_CapEx"] = capex
            total_capex += capex

            # Calculate opex based on the cost of feedstock and total feedstock used
            total_feedstock_used = rated_capacity * 8760
            opex = total_feedstock_used * price
            outputs[f"{feedstock_name}_OpEx"] = opex
            total_opex += opex

        # Set total CapEx and OpEx
        outputs["CapEx"] = total_capex
        outputs["OpEx"] = total_opex
