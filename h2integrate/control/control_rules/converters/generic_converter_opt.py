import pyomo.environ as pyo
from pyomo.network import Port, Expression
from attrs import field, define

from h2integrate.control.control_rules.converters.generic_converter import (
    PyomoDispatchGenericConverter
)
from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseConfig

@define
class PyomoDispatchGenericConverterMinOperatingCostsConfig(PyomoRuleBaseConfig):
    """
    Configuration class for the PyomoDispatchGenericConverterMinOperatingCostsConfig.

    This class defines the parameters required to configure the `PyomoRuleBaseConfig`.

    Attributes:
        commodity_cost_per_production (float): cost of the commodity per production (in $/kWh).
    """

    commodity_cost_per_production: str = field()


class PyomoDispatchGenericConverterMinOperatingCosts(PyomoDispatchGenericConverter):
    def setup(self):
        self.config = PyomoDispatchGenericConverterMinOperatingCostsConfig.from_dict(
            self.options["tech_config"]["model_inputs"]["dispatch_rule_parameters"]
        )
        super().setup()

    def initialize_parameters(self, commodity_in: list, commodity_demand: list):
        """Initialize parameters method."""
        self.cost_per_production = (
            self.config["commodity_cost_per_production"]
        )

    def _create_variables(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create generic converter variables to add to Pyomo model instance.

        Args:
            pyomo_model (pyo.ConcreteModel): pyomo_model the variables should be added to.
            tech_name (str): The name or key identifying the technology for which
            variables are created.

        """
        setattr(
            pyomo_model,
            f"{tech_name}_{self.config.commodity_name}",
            pyo.Var(
                doc=f"{self.config.commodity_name} production \
                    from {tech_name} [{self.config.commodity_storage_units}]",
                domain=pyo.NonNegativeReals,
                bounds=(0, pyomo_model.available_production),
                units=eval("pyo.units." + self.config.commodity_storage_units),
                initialize=0.0,
            ),
        )
        return getattr(
            pyomo_model,
            f"{tech_name}_{self.config.commodity_name}",
        ), 0.0  # load var is zero for converters

    def _create_ports(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create generic converter port to add to pyomo model instance.

        Args:
            pyomo_model (pyo.ConcreteModel): pyomo_model the ports should be added to.
            tech_name (str): The name or key identifying the technology for which
            ports are created.

        """
        setattr(
            pyomo_model,
            f"{tech_name}_port",
            Port(
                initialize={
                    f"{tech_name}_{self.config.commodity_name}": getattr(
                        pyomo_model, f"{tech_name}_{self.config.commodity_name}"
                    )
                }
            ),
        )
        return getattr(
            pyomo_model,
            f"{tech_name}_port",
        )

    def _create_parameters(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create technology Pyomo parameters to add to the Pyomo model instance.

        Method is currently passed but this can serve as a template to add parameters to the Pyomo
        model instance.

        Args:
            pyomo_model (pyo.ConcreteModel): pyomo_model that parameters are added to.
            tech_name (str): The name or key identifying the technology for which
            parameters are created.

        """
        ##################################
        # Parameters                     #
        ##################################
        pyomo_model.time_duration = pyo.Param(
            doc=pyomo_model.name + " time step [hour]",
            default=1.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=pyo.units.hr,
        )
        pyomo_model.cost_per_production = pyo.Param(
            doc="Production cost for generator [$/"
            + self.config.commodity_storage_units
            + "]",
            default=0.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units.USD / pyo.units." + self.config.commodity_storage_units),
        )
        pyomo_model.available_production = pyo.Param(
            doc="Available production for the generator ["
            + self.config.commodity_storage_units
            + "]",
            default=0.0,
            within=pyo.Reals,
            mutable=True,
            units=eval("pyo.units." + self.config.commodity_storage_units),
        )

        pass

    def _create_constraints(self, pyomo_model: pyo.ConcreteModel, tech_name: str):
        """Create technology Pyomo parameters to add to the Pyomo model instance.

        Method is currently passed but this can serve as a template to add constraints to the Pyomo
        model instance.

        Args:
            pyomo_model (pyo.ConcreteModel): pyomo_model that constraints are added to.
            tech_name (str): The name or key identifying the technology for which
            constraints are created.

        """

        pass

    def update_time_series_parameters(self, start_time: int,
                                      commodity_in:list,
                                      commodity_demand:list,
                                      time_commodity_met_value:list
                                      ):
        """Update time series parameters method.

        Args:
            start_time (int): The starting time index for the update.
            commodity_in (list): List of commodity input values for each time step.
        """
        self.available_production = [commodity_in[t]
                                        for t in self.blocks.index_set()]

    @property
    def available_production(self) -> list:
        """Available generation.

        Returns:
            list: List of available generation.

        """
        return [
            self.blocks[t].available_production.value for t in self.blocks.index_set()
        ]

    @available_production.setter
    def available_production(self, resource: list):
        if len(resource) == len(self.blocks):
            for t, gen in zip(self.blocks, resource):
                self.blocks[t].available_production.set_value(
                    round(gen, self.round_digits)
                )
        else:
            raise ValueError(
                f"'resource' list ({len(resource)}) must be the same length as\
                time horizon ({len(self.blocks)})"
            )

    @property
    def cost_per_production(self) -> float:
        """Cost per generation [$/commodity_storage_units]."""
        for t in self.blocks.index_set():
            return self.blocks[t].cost_per_production.value

    @cost_per_production.setter
    def cost_per_production(self, om_dollar_per_kwh: float):
        for t in self.blocks.index_set():
            self.blocks[t].cost_per_production.set_value(
                round(om_dollar_per_kwh, self.round_digits)
            )

    def min_operating_cost_objective(self, hybrid_blocks, tech_name: str):
        """Wind instance of minimum operating cost objective.

        Args:
            hybrid_blocks (Pyomo.block): A generalized container for defining hierarchical
                models by adding modeling components as attributes.

        """
        self.obj = Expression(
            expr=sum(
            hybrid_blocks[t].time_weighting_factor
            * self.blocks[t].time_duration
            * self.blocks[t].cost_per_production
            * getattr(
            hybrid_blocks,
            f"{tech_name}_{self.config.commodity_name}",
            )[t]
            for t in hybrid_blocks.index_set()
            )
        )
