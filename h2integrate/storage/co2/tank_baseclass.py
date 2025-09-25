import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import CostModelBaseConfig
from h2integrate.core.model_baseclasses import CostModelBaseClass


class CO2TankPerformanceModel(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        config_details = self.options["tech_config"]["details"]
        self.add_input(
            "co2_in",
            val=0.0,
            shape_by_conn=True,
            copy_shape="co2_out",
            units="kg/h",
            desc="CO2 input over a year",
        )
        self.add_input("initial_co2", val=0.0, units="kg", desc="Initial amount of co2 in the tank")
        self.add_input(
            "total_capacity",
            val=float(config_details["total_capacity"]),
            units="kg",
            desc="Total storage capacity",
        )
        self.add_input(
            "co2_out",
            val=0.0,
            shape_by_conn=True,
            copy_shape="co2_in",
            units="kg/h",
            desc="CO2 output over a year",
        )
        self.add_output(
            "stored_co2",
            val=0.0,
            shape_by_conn=True,
            copy_shape="co2_in",
            units="kg",
            desc="Amount of co2 stored",
        )

    def compute(self, inputs, outputs):
        initial_co2 = inputs["initial_co2"]
        co2_in = inputs["co2_in"]
        co2_out = inputs["co2_out"]

        outputs["stored_co2"] = initial_co2 + co2_in - co2_out


@define
class TankCostModelConfig(CostModelBaseConfig):
    total_capacity: float = field()


class CO2TankCostModel(CostModelBaseClass):
    def setup(self):
        self.config = TankCostModelConfig.from_dict(self.options["tech_config"]["details"])
        super().setup()
        self.add_input(
            "total_capacity",
            val=self.config.total_capacity,
            units="kg",
            desc="Total storage capacity",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        outputs["CapEx"] = inputs["total_capacity"] * 0.1
        outputs["OpEx"] = inputs["total_capacity"] * 0.01
