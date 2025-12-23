import pyomo.environ as pyo
from pyomo.network import Port
from attrs import field, define

from h2integrate.control.control_rules.converters.generic_converter import (
    PyomoDispatchGenericConverter
)
from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseConfig

# @define
# class PyomoDispatchGenericConverterMinOperatingCostsConfig(PyomoRuleBaseConfig):
#     """
#     Configuration class for the PyomoDispatchGenericConverterMinOperatingCostsConfig.

#     This class defines the parameters required to configure the `PyomoRuleBaseConfig`.
"""
Attributes:
    commodity_cost_per_production (float): cost of the commodity per production (in $/kWh).
"""

commodity_cost_per_production: float = field()


class PyomoDispatchGenericConverterMinOperatingCosts:

    def __init__(
        self,
        commodity_info: dict,
        pyomo_model: pyo.ConcreteModel,
        index_set: pyo.Set,
        block_set_name: str = "converter",
    ):

        self.round_digits = int(4)
        self.block_set_name = block_set_name
        self.commodity_name = commodity_info["commodity_name"]
        self.commodity_storage_units = commodity_info["commodity_storage_units"]
        print(self.commodity_name, self.commodity_storage_units)

        self._model = pyomo_model
        self._blocks = pyo.Block(index_set, rule=self.dispatch_block_rule_function)
        setattr(self.model, self.block_set_name, self.blocks)
        self.time_duration = [1.0] * len(self.blocks.index_set())

        print("HEYYYY")

    def initialize_parameters(self, commodity_in: list, commodity_demand: list,
                              dispatch_inputs: dict):
        """Initialize parameters method.
        """

        self.cost_per_production = dispatch_inputs["cost_per_production"]

    def dispatch_block_rule_function(self, pyomo_model: pyo.ConcreteModel):
        """
        Creates and initializes pyomo dispatch model components for a specific technology.

        This method sets up all model elements (parameters, variables, constraints,
        and ports) associated with a technology block within the dispatch model.
        It is typically called in the setup_pyomo() method of the PyomoControllerBaseClass.

        Args:
            pyomo_model (pyo.ConcreteModel): The Pyomo model to which the technology
                components will be added.
            tech_name (str): The name or key identifying the technology (e.g., "battery",
                "electrolyzer") for which model components are created.
        """
        # Parameters
        self._create_parameters(pyomo_model)
        # Variables
        self._create_variables(pyomo_model)
        # Constraints
        self._create_constraints(pyomo_model)
        # Ports
        self._create_ports(pyomo_model)

    # Base model setup
    def _create_variables(self, pyomo_model: pyo.ConcreteModel):
        """Create generic converter variables to add to Pyomo model instance.

        Args:
            pyomo_model (pyo.ConcreteModel): pyomo_model the variables should be added to.
            tech_name (str): The name or key identifying the technology for which
            variables are created.

        """
        setattr(
            pyomo_model,
            f"{self.block_set_name}_{self.commodity_name}",
            pyo.Var(
                doc=f"{self.commodity_name} production \
                    from {self.block_set_name} [{self.commodity_storage_units}]",
                domain=pyo.NonNegativeReals,
                bounds=(0, pyomo_model.available_production),
                units=eval("pyo.units." + self.commodity_storage_units),
                initialize=0.0,
            ),
        )

    def _create_ports(self, pyomo_model: pyo.ConcreteModel):
        """Create generic converter port to add to pyomo model instance.

        Args:
            pyomo_model (pyo.ConcreteModel): pyomo_model the ports should be added to.
            tech_name (str): The name or key identifying the technology for which
            ports are created.

        """
        pyomo_model.port = Port()
        pyomo_model.port.add(
            getattr(
                pyomo_model, f"{self.block_set_name}_{self.commodity_name}"
            ),
        )

    def _create_parameters(self, pyomo_model: pyo.ConcreteModel):
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
            + self.commodity_storage_units
            + "]",
            default=0.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=eval("pyo.units.USD / pyo.units." + self.commodity_storage_units+"h"),
        )
        pyomo_model.available_production = pyo.Param(
            doc="Available production for the generator ["
            + self.commodity_storage_units
            + "]",
            default=0.0,
            within=pyo.Reals,
            mutable=True,
            units=eval("pyo.units." + self.commodity_storage_units),
        )

        pass

    def _create_constraints(self, pyomo_model: pyo.ConcreteModel):
        """Create technology Pyomo parameters to add to the Pyomo model instance.

        Method is currently passed but this can serve as a template to add constraints to the Pyomo
        model instance.

        Args:
            pyomo_model (pyo.ConcreteModel): pyomo_model that constraints are added to.
            tech_name (str): The name or key identifying the technology for which
            constraints are created.

        """

        pass

    # Update time series parameters for next optimization window
    def update_time_series_parameters(self, start_time: int,
                                      commodity_in:list,
                                      commodity_demand:list,
                                    #   time_commodity_met_value:list
                                      ):
        """Update time series parameters method.

        Args:
            start_time (int): The starting time index for the update.
            commodity_in (list): List of commodity input values for each time step.
        """
        self.time_duration = [1.0] * len(self.blocks.index_set())
        self.available_production = [commodity_in[t]
                                        for t in self.blocks.index_set()]

    # Objective functions
    def min_operating_cost_objective(self, hybrid_blocks, tech_name: str):
        """Wind instance of minimum operating cost objective.

        Args:
            hybrid_blocks (Pyomo.block): A generalized container for defining hierarchical
                models by adding modeling components as attributes.

        """
        # commodity_name = getattr(
        #     hybrid_blocks,
        #     f"{tech_name}_{self.commodity_name}",
        # )
        commodity_set = [getattr(hybrid_blocks[t], f"{tech_name}_{self.commodity_name}")
                         for t in self.blocks.index_set()]
        i = hybrid_blocks.index_set()[1]
        print("Units???",self.blocks[i].time_duration.get_units())
        print(commodity_set[i].get_units())
        print(self.blocks[i].cost_per_production.get_units())
        self.obj =sum(
            hybrid_blocks[t].time_weighting_factor
            * self.blocks[t].time_duration
            * self.blocks[t].cost_per_production
            # * commodity_set[t].value
            * getattr(hybrid_blocks[t], f"{tech_name}_{self.commodity_name}")
            for t in hybrid_blocks.index_set()
            )
        # print(self.obj.get_units())
        return self.obj

    # System-level functions
    def _create_hybrid_port(self, hybrid_model: pyo.ConcreteModel, tech_name: str):
        """Create hybrid ports for storage to add to pyomo model instance.

        Args:
            hybrid_model (pyo.ConcreteModel): hybrid_model the ports should be added to.
            tech_name (str): The name or key identifying the technology for which
            ports are created.
        """
        setattr(
            hybrid_model,
            f"{tech_name}_port",
            Port(
                initialize={
                    f"{tech_name}_{self.commodity_name}": getattr(
                        hybrid_model, f"{tech_name}_{self.commodity_name}"
                    )
                }
            ),
        )
        return getattr(
            hybrid_model,
            f"{tech_name}_port",
        )

    def _create_hybrid_variables(self, hybrid_model: pyo.ConcreteModel, tech_name: str):
        """Create hybrid variables for generic converter technology to add to pyomo model instance.

        Args:
            hybrid_model (pyo.ConcreteModel): hybrid_model the variables should be added to.
            tech_name (str): The name or key identifying the technology for which
            variables are created.
        """
        setattr(
            hybrid_model,
            f"{tech_name}_{self.commodity_name}",
            pyo.Var(
                doc=f"{self.commodity_name} production \
                    from {tech_name} [{self.commodity_storage_units}]",
                domain=pyo.NonNegativeReals,
                units=eval("pyo.units." + self.commodity_storage_units),
                initialize=0.0,
            ),
        )
        return getattr(
            hybrid_model,
            f"{tech_name}_{self.commodity_name}",
        ), 0.0  # load var is zero for converters

    # Property getters and setters for time series parameters
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

    @property
    def time_duration(self) -> list:
        """Time duration."""
        return [self.blocks[t].time_duration.value for t in self.blocks.index_set()]

    @time_duration.setter
    def time_duration(self, time_duration: list):
        if len(time_duration) == len(self.blocks):
            for t, delta in zip(self.blocks, time_duration):
                self.blocks[t].time_duration = round(delta, self.round_digits)
        else:
            raise ValueError(
                self.time_duration.__name__
                + " list must be the same length as time horizon"
            )

    @property
    def blocks(self) -> pyo.Block:
        return self._blocks

    @property
    def model(self) -> pyo.ConcreteModel:
        return self._model
