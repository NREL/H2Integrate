import importlib

from attrs import field, define

from h2integrate.core.utilities import (
    BaseConfig,
    merge_shared_cost_inputs,
    merge_shared_finance_inputs,
    merge_shared_performance_inputs,
)
from h2integrate.converters.methanol.methanol_baseclass import (
    MethanolCostBaseClass,
    MethanolFinanceBaseClass,
    MethanolPerformanceBaseClass,
)


@define
class MethanolPerformanceConfig(BaseConfig):
    conversion_tech: str = field()
    plant_capacity_kgpy: float = field()
    capacity_factor: float = field()


class MethanolPlantPerformanceModel(MethanolPerformanceBaseClass):
    """
    An OpenMDAO component that wraps various methanol performance models.
    Takes in conversion technology and plant capacity from config and computes the plant's flows.
    """

    def setup(self):
        super().setup()
        self.config = MethanolPerformanceConfig.from_dict(
            merge_shared_performance_inputs(self.options["tech_config"]["model_inputs"])
        )

        # Import performance model for specified tech
        tech = self.config.conversion_tech
        import_path = "h2integrate.simulation.technologies.methanol." + tech
        Performance = importlib.import_module(import_path).Performance
        self.methanol = Performance()

        # Declare inputs and outputs - combination of values from config and model
        config_values = self.config.as_dict()
        # Config values overwrite any defaults from baseclass
        values = self.values
        if config_values:
            for key, value in config_values.items():
                values[key] = value
            self.values = values
        # Add in tech-specific variables and values
        tech_dec_table_inputs = self.methanol.dec_table_inputs
        tech_values = self.methanol.values
        self.declare_from_table(tech_dec_table_inputs, tech_values)

    def compute(self, inputs, outputs):
        # Run the methanol plant model using the input signals
        performances = self.methanol.run_performance_model(inputs)
        for key, performance in performances.items():
            outputs[key] = performance


@define
class MethanolCostConfig(BaseConfig):
    conversion_tech: str = field()
    plant_capacity_kgpy: float = field()


class MethanolPlantCostModel(MethanolCostBaseClass):
    """
    An OpenMDAO component that wraps various methanol cost models.
    Takes in conversion technology and plant capacity from config and computes the plant's costs.
    """

    def setup(self):
        super().setup()
        self.config = MethanolCostConfig.from_dict(
            merge_shared_cost_inputs(self.options["tech_config"]["model_inputs"])
        )
        # Import cost model for specified tech and model
        tech = self.config.conversion_tech
        import_path = "h2integrate.simulation.technologies.methanol." + tech
        Cost = importlib.import_module(import_path).Cost
        self.cost_model = Cost()

        # Declare inputs and outputs - combination of values from config and model
        config_values = self.config.as_dict()
        # Config values overwrite any defaults from baseclass
        values = self.values
        if config_values:
            for key, value in config_values.items():
                values[key] = value
            self.values = values
        # Add in tech-specific variables and values
        tech_dec_table_inputs = self.cost_model.dec_table_inputs
        tech_values = self.cost_model.values
        self.declare_from_table(tech_dec_table_inputs, tech_values)

    def compute(self, inputs, outputs):
        # Call the cost model to compute costs
        cost_model = self.cost_model
        costs = cost_model.run_cost_model(inputs)
        for key, cost in costs.items():
            outputs[key] = cost


@define
class MethanolFinanceConfig(BaseConfig):
    conversion_tech: str = field()
    plant_capacity_kgpy: float = field()
    discount_rate: float = field()
    tasc_toc_multiplier: float = field()


class MethanolPlantFinanceModel(MethanolFinanceBaseClass):
    """
    An OpenMDAO component that wraps various methanol finance models.
    Takes in conversion technology, plant capacity, and financial constants from config and
    computes the plant's finances.
    """

    def setup(self):
        super().setup()
        self.config = MethanolFinanceConfig.from_dict(
            merge_shared_finance_inputs(self.options["tech_config"]["model_inputs"])
        )
        # Import finance model for specified tech and model
        tech = self.config.conversion_tech
        import_path = "h2integrate.simulation.technologies.methanol." + tech
        Finance = importlib.import_module(import_path).Finance
        self.finance_model = Finance()

        # Declare inputs and outputs - combination of values from config and model
        config_values = self.config.as_dict()
        # Config values overwrite any defaults from baseclass
        values = self.values
        if config_values:
            for key, value in config_values.items():
                values[key] = value
            self.values = values
        # Add in tech-specific variables and values
        tech_dec_table_inputs = self.finance_model.dec_table_inputs
        tech_values = self.finance_model.values
        self.declare_from_table(tech_dec_table_inputs, tech_values)

    def compute(self, inputs, outputs):
        # Call the finance model to compute finances
        finance_model = self.finance_model
        finances = finance_model.run_finance_model(inputs)
        for key, finance in finances.items():
            outputs[key] = finance
