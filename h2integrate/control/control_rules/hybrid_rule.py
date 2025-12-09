import pyomo.environ as pyo
from pyomo.network import Port, Arc
from attrs import field, define

# from h2integrate.control.control_rules.pyomo_rule_baseclass import PyomoRuleBaseClass


# @define
# class PyomoDispatchGenericConverterMinOperatingCostsConfig(PyomoRuleBaseConfig):
#     """
#     Configuration class for the PyomoDispatchGenericConverterMinOperatingCostsConfig.

#     This class defines the parameters required to configure the `PyomoRuleBaseConfig`.

#     Attributes:
#         commodity_cost_per_production (float): cost of the commodity per production (in $/kWh).
#     """

#     commodity_cost_per_production: str = field()


class PyomoDispatchPlantRule:
    def __init__(
        self,
        pyomo_model: pyo.ConcreteModel,
        index_set: pyo.Set,
        source_techs: dict,
        tech_dispatch_models: pyo.ConcreteModel,
        dispatch_options: dict,
        block_set_name: str = "hybrid",
    ):
        # self.config = PyomoDispatchGenericConverterMinOperatingCostsConfig.from_dict(
        #     self.options["tech_config"]["model_inputs"]["dispatch_rule_parameters"]
        # )


        self.source_techs = source_techs
        self.options = dispatch_options
        self.power_source_gen_vars = {key: [] for key in index_set}
        self.tech_dispatch_models = tech_dispatch_models
        self.load_vars = {key: [] for key in index_set}
        self.ports = {key: [] for key in index_set}
        self.arcs = []

        self.block_set_name = block_set_name
        self.round_digits = int(4)

        self._model = pyomo_model
        self._blocks = pyo.Block(index_set, rule=self.dispatch_block_rule)
        setattr(self.model, self.block_set_name, self.blocks)


        super().setup()

    def dispatch_block_rule(self, hybrid, t):
        ##################################
        # Parameters                     #
        ##################################
        self._create_parameters(hybrid)
        ##################################
        # Variables / Ports              #
        ##################################
        self._create_variables_and_ports(hybrid, t)
        ##################################
        # Constraints                    #
        ##################################
        self._create_hybrid_constraints(hybrid, t)


    def initialize_parameters(self, commodity_in: list, commodity_demand: list):
        """Initialize parameters method."""
        self.time_weighting_factor = (
            self.options.time_weighting_factor
        )  # Discount factor
        for tech in self.source_techs.keys():
            pyomo_block = getattr(self.tech_dispatch_models, tech)
            pyomo_block.initialize_parameters(commodity_in, commodity_demand)

    def _create_variables_and_ports(self, hybrid, t):
        for tech in self.source_techs.keys():
            pyomo_block = getattr(self.tech_dispatch_models, tech)
            gen_var, load_var = pyomo_block._create_variables(hybrid, tech)

            self.power_source_gen_vars[t].append(gen_var)
            self.load_vars[t].append(load_var)
            self.ports[t].append(
                pyomo_block._create_port(hybrid)
            )

    @staticmethod
    def _create_parameters(hybrid):
        hybrid.time_weighting_factor = pyo.Param(
            doc="Exponential time weighting factor [-]",
            initialize=1.0,
            within=pyo.PercentFraction,
            mutable=True,
            units=pyo.units.dimensionless,
        )

    def _create_hybrid_constraints(self, hybrid, t):
        hybrid.production_total = pyo.Constraint(
            doc="hybrid system generation total",
            rule=hybrid.system_production == sum(self.power_source_gen_vars[t]),
        )

        hybrid.load_total = pyo.Constraint(
            doc="hybrid system load total",
            rule=hybrid.system_load == sum(self.load_vars[t]),
        )

    def create_arcs(self):
        ##################################
        # Arcs                           #
        ##################################
        for tech in self.source_techs.keys():
            pyomo_block = getattr(self.tech_dispatch_models, tech)
            def arc_rule(m, t):
                source_port = self.pyomo_block.blocks[t].port
                destination_port = getattr(self.blocks[t], tech + "_port")
                return {"source": source_port, "destination": destination_port}

            setattr(
                self.model,
                tech + "_hybrid_arc",
                Arc(self.blocks.index_set(), rule=arc_rule),
            )
            self.arcs.append(getattr(self.model, tech + "_hybrid_arc"))

        pyo.TransformationFactory("network.expand_arcs").apply_to(self.model)

    def update_time_series_parameters(self, start_time: int):
        for tech in self.source_techs.keys():
            pyomo_block = getattr(self.tech_dispatch_models, tech)
            pyomo_block.update_time_series_parameters(start_time)

    def update_time_series_parameters(self, start_time: int, commodity_in:list):
        """Update time series parameters method.

        Args:
            start_time (int): Start time.

        Returns:
            None

        """
        n_horizon = len(self.blocks.index_set())
        production = commodity_in
        if start_time + n_horizon > len(production):
            horizon_gen = list(production[start_time:])
            horizon_gen.extend(list(production[0 : n_horizon - len(horizon_gen)]))
        else:
            horizon_gen = production[start_time : start_time + n_horizon]

        if len(horizon_gen) < len(self.blocks):
            raise RuntimeError(
                f"Dispatch parameter update error at start_time {start_time}: System model "
                f"{type(self._system_model)} production profile should have at least {len(self.blocks)} "
                f"length but has only {len(production)}"
            )
        self.available_production = [gen_kw / 1e3 for gen_kw in horizon_gen]

    @property
    def blocks(self) -> pyo.Block:
        return self._blocks

    @property
    def model(self) -> pyo.ConcreteModel:
        return self._model
