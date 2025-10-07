import openmdao.api as om
from attrs import field, define
from ard.api import set_up_ard_model

from h2integrate.core.utilities import BaseConfig, CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.model_baseclasses import CostModelBaseClass


class WindArdCostComponent(CostModelBaseClass):
    def setup(self):
        self.config = CostModelBaseConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

        super().setup()

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        pass


@define
class WindPlantArdModelConfig(BaseConfig):
    ard_system: dict = field()
    ard_data_path: str = field()


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

        self.add_subsystem(
            "wind_ard_cost",
            WindArdCostComponent(
                driver_config=self.options["driver_config"],
                plant_config=self.options["plant_config"],
                tech_config=self.options["tech_config"],
            ),
            promotes=["cost_year", "VarOpEx"],
        )

        # add ard sub-problem
        ard_input_dict = self.options["tech_config"]["model_inputs"]["performance_parameters"][
            "ard_system"
        ]
        ard_data_path = self.options["tech_config"]["model_inputs"]["performance_parameters"][
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
