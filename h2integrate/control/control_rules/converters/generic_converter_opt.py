import pyomo.environ as pyo
from pyomo.network import Port
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
        commodity_cost_per_generation (float): cost of the commodity per generation (in $/kWh).
    """

    commodity_cost_per_generation: str = field()


class PyomoDispatchGenericConverterMinOperatingCosts(PyomoDispatchGenericConverter):
    def setup(self):
        self.config = PyomoDispatchGenericConverterMinOperatingCostsConfig.from_dict(
            self.options["tech_config"]["model_inputs"]["dispatch_rule_parameters"]
        )
        super().setup()

    def initialize_parameters(self):
        """Initialize parameters method."""
        self.cost_per_generation = (
            self.config["commodity_cost_per_generation"]
        )

    def min_operating_cost_objective(self, pyomo_model: pyo.ConcreteModel, hybrid_blocks):
        """ Create generice converter objective call to add to Pyomo model instance.

        Args:
            pyomo_model (pyo.ConcreteModel): pyomo_model the variables should be added to.
            tech_name (str): The name or key identifying the technology for which
            variables are created.
        """
        self.obj = sum(
            pyomo_model.time_weighting_factor[t]
            * pyomo_model.time_duration
            * pyomo_model.cost_per_generation
            * hybrid_blocks[t].generic_generation
            for t in hybrid_blocks.index_set()
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
                doc=f"{self.config.commodity_name} generation \
                    from {tech_name} [{self.config.commodity_storage_units}]",
                domain=pyo.NonNegativeReals,
                bounds=(0, pyomo_model.available_generation),
                units=eval("pyo.units." + self.config.commodity_storage_units),
                initialize=0.0,
            ),
        )

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
        pyomo_model.cost_per_generation = pyo.Param(
            doc="Generation cost for generator [$/MWh]",
            default=0.0,
            within=pyo.NonNegativeReals,
            mutable=True,
            units=pyo.units.USD / pyo.units.MWh,
        )
        pyomo_model.available_generation = pyo.Param(
            doc="Available generation for the generator [MW]",
            default=0.0,
            within=pyo.Reals,
            mutable=True,
            units=pyo.units.MW,
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

    def initialize_parameters(self):
        """Initialize parameters method."""
        self.cost_per_generation = (
            self._financial_model.value("om_capacity")[0] * 1e3 / 8760
        )    
