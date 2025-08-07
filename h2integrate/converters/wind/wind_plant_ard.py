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
        ard_input_dict = self.options["tech_config"]["shared_inputs"]["ard_system"]

        ard_prob = ard.api.set_up_ard_model(input_dict=ard_input_dict)

        self.add_subsystem(
            "wind_plant_ard",
            ard_prob.model,
            promotes=[
                "(layout2aep.aepFLORIS.power_farm, electricity_out)",
                "(tcc.tcc, CapEx)",
                "(opex.opex, OpEx)",
            ],
        )
