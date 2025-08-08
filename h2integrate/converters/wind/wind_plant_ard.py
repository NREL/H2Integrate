import ard
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig


@define
class WindPlantArdModelConfig(BaseConfig):
    ard_system: dict = field()


class ArdWindPlantModel(om.Group):
    """
    Create Ard group and promote Ard names into the H2Integrate naming conventions
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        ard_input_dict = self.options["tech_config"]["model_inputs"]["shared_parameters"][
            "ard_system"
        ]
        ard_data_path = self.options["tech_config"]["model_inputs"]["shared_parameters"][
            "ard_data_path"
        ]

        ard_prob = ard.api.set_up_ard_model(input_dict=ard_input_dict, root_data_path=ard_data_path)

        import pdb

        pdb.set_trace()
        # add ard to the h2i model as a sub-problem
        subprob_ard = om.SubmodelComp(
            problem=ard_prob,
            inputs=[],
            outputs=[
                ("aepFLORIS.power_farm", "electricity_out"),
                ("tcc.tcc", "CapEx"),
                ("opex.opex", "OpEx"),
            ],
        )

        self.add_subsystem(
            "ard_sub_prob",
            subprob_ard,
            promotes=["*"],
        )
