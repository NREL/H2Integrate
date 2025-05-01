import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import (
    BaseConfig,
    merge_shared_cost_inputs,
    merge_shared_performance_inputs,
)
from h2integrate.simulation.technologies.ammonia.ammonia import (
    run_ammonia_model,
    run_ammonia_cost_model,
)


@define
class Feedstocks(BaseConfig):
    """
    Represents the costs and consumption rates of various feedstocks and resources
    used in ammonia production.

    Attributes:
        electricity_cost (float): Cost per MWh of electricity.
        hydrogen_cost (float): Cost per kg of hydrogen.
        cooling_water_cost (float): Cost per gallon of cooling water.
        iron_based_catalyst_cost (float): Cost per kg of iron-based catalyst.
        oxygen_cost (float): Cost per kg of oxygen.
        electricity_consumption (float): Electricity consumption in MWh per kg of
            ammonia production, default is 0.1207 / 1000.
        hydrogen_consumption (float): Hydrogen consumption in kg per kg of ammonia
            production, default is 0.197284403.
        cooling_water_consumption (float): Cooling water consumption in gallons per
            kg of ammonia production, default is 0.049236824.
        iron_based_catalyst_consumption (float): Iron-based catalyst consumption in kg
            per kg of ammonia production, default is 0.000091295354067341.
        oxygen_byproduct (float): Oxygen byproduct in kg per kg of ammonia production,
            default is 0.29405077250145.
    """

    electricity_cost: float = field()
    cooling_water_cost: float = field()
    iron_based_catalyst_cost: float = field()
    oxygen_cost: float = field()
    hydrogen_cost: float = field(default=None)
    electricity_consumption: float = field(default=0.1207 / 1000)
    hydrogen_consumption: float = field(default=0.197284403)
    cooling_water_consumption: float = field(default=0.049236824)
    iron_based_catalyst_consumption: float = field(default=0.000091295354067341)
    oxygen_byproduct: float = field(default=0.29405077250145)


@define
class AmmoniaPerformanceModelConfig(BaseConfig):
    plant_capacity_kgpy: float = field()
    plant_capacity_factor: float = field()


class AmmoniaPerformanceModel(om.ExplicitComponent):
    """
    An OpenMDAO component for modeling the performance of an ammonia plant.
    Computes annual ammonia production based on plant capacity and capacity factor.
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = AmmoniaPerformanceModelConfig.from_dict(
            merge_shared_performance_inputs(self.options["tech_config"]["model_inputs"])
        )
        self.add_input("hydrogen", val=0.0, shape_by_conn=True, copy_shape="ammonia", units="kg/h")
        self.add_output("ammonia", val=0.0, shape_by_conn=True, copy_shape="hydrogen", units="kg/h")
        self.add_output("total_ammonia_produced", val=0.0, units="kg/year")

    def compute(self, inputs, outputs):
        ammonia_production_kgpy = run_ammonia_model(
            self.config.plant_capacity_kgpy,
            self.config.plant_capacity_factor,
        )
        outputs["ammonia"] = ammonia_production_kgpy / len(inputs["hydrogen"])
        outputs["total_ammonia_produced"] = ammonia_production_kgpy


@define
class AmmoniaCostModelConfig(BaseConfig):
    """
    Configuration inputs for the ammonia cost model, including plant capacity and
    feedstock details.

    Attributes:
        plant_capacity_kgpy (float): Annual production capacity of the plant in kg.
        plant_capacity_factor (float): The ratio of actual production to maximum
            possible production over a year.
        feedstocks (dict): A dictionary that is passed to the `Feedstocks` class detailing the
            costs and consumption rates of resources used in production.
    """

    plant_capacity_kgpy: float = field()
    plant_capacity_factor: float = field()
    feedstocks: dict = field(converter=Feedstocks.from_dict)


class AmmoniaCostModel(om.ExplicitComponent):
    """
    An OpenMDAO component for calculating the costs associated with ammonia production.
    Includes CapEx, OpEx, and byproduct credits.
    """

    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        # Inputs for cost model configuration
        self.add_input(
            "plant_capacity_kgpy", val=0.0, units="kg/year", desc="Annual plant capacity"
        )
        self.add_input("plant_capacity_factor", val=0.0, units=None, desc="Capacity factor")
        self.add_output("CapEx", val=0.0, units="USD", desc="Total capital expenditures")
        self.add_output("OpEx", val=0.0, units="USD/year", desc="Total fixed operating costs")
        self.add_output(
            "variable_cost_in_startup_year", val=0.0, units="USD", desc="Variable costs"
        )
        self.add_output("credits_byproduct", val=0.0, units="USD", desc="Byproduct credits")

        self.cost_config = AmmoniaCostModelConfig.from_dict(
            merge_shared_cost_inputs(self.options["tech_config"]["model_inputs"])
        )

        if self.cost_config.feedstocks.hydrogen_cost is None:
            self.add_input("LCOH", val=0.0, units="USD/kg", desc="Levelized cost of hydrogen")

    def compute(self, inputs, outputs):
        if self.cost_config.feedstocks.hydrogen_cost is None:
            self.cost_config.feedstocks.hydrogen_cost = inputs["LCOH"]

        cost_model_outputs = run_ammonia_cost_model(self.cost_config)

        outputs["CapEx"] = cost_model_outputs.capex_total
        outputs["OpEx"] = cost_model_outputs.total_fixed_operating_cost
        outputs["variable_cost_in_startup_year"] = cost_model_outputs.variable_cost_in_startup_year
        outputs["credits_byproduct"] = cost_model_outputs.credits_byproduct
