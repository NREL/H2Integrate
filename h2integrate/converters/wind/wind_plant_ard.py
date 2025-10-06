import openmdao.api as om
from attrs import field, define
from ard.api import set_up_ard_model

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs


class cost_year_var_om_component(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("cost_year")
        self.options.declare("var_opex")
        self.options.declare("plant_config", types=dict)

    def setup(self):
        lifetime = self.options["plant_config"]["plant"]["plant_life"]
        self.add_output("VarOpEx", val=[self.options["var_opex"]] * lifetime)
        # Discrete Inputs
        self.add_discrete_output("cost_year", val=self.options["cost_year"])

        # Continuous Outputs
        self.add_output("blade_solidity", 0.0, desc="Blade solidity")

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pass


@define
class WindPlantArdModelConfig(BaseConfig):
    ard_system: dict = field()
    ard_data_path: str = field()
    # cost_year: int = field()
    # var_opex: float = field()


class ArdWindPlantModel(om.Group):
    """
    Create Ard group and promote Ard names into the H2Integrate naming conventions
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = WindPlantArdModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        # add cost year and var opex
        # cost_year = self.config.cost_year
        cost_year = self.options["tech_config"]["model_inputs"]["cost_parameters"]["cost_year"]
        # var_opex = self.config.var_opex
        var_opex = self.options["tech_config"]["model_inputs"]["cost_parameters"]["var_opex"]
        self.add_subsystem(
            "var_opex_comp",
            cost_year_var_om_component(
                cost_year=cost_year, var_opex=var_opex, plant_config=self.options["plant_config"]
            ),
            promotes=["*"],
        )

        # add ard sub-problem
        ard_input_dict = self.options["tech_config"]["model_inputs"]["shared_parameters"][
            "ard_system"
        ]
        ard_data_path = self.options["tech_config"]["model_inputs"]["shared_parameters"][
            "ard_data_path"
        ]

        ard_prob = set_up_ard_model(input_dict=ard_input_dict, root_data_path=ard_data_path)

        # add ard to the h2i model as a sub-problem
        subprob_ard = om.SubmodelComp(
            problem=ard_prob,
            inputs=[
                "spacing_primary",
                "spacing_secondary",
                "angle_orientation",
                "angle_skew",
                "x_substations",
                "y_substations",
            ],
            outputs=[
                ("aepFLORIS.power_farm", "electricity_out"),
                ("tcc.tcc", "CapEx"),
                ("opex.opex", "OpEx"),
                "boundary_distances",
                "turbine_spacing",
            ],
        )

        self.add_subsystem(
            "ard_sub_prob",
            subprob_ard,
            promotes=["*"],
        )
