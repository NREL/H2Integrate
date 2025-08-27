import openmdao.api as om


class CombinerPerformanceModel(om.ExplicitComponent):
    """
    Combine power from two sources into one output without losses.

    This component is purposefully simple; a more realistic case might include
    losses or other considerations from power electronics.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("electricity_in1", val=0.0, shape_by_conn=True, units="kW")
        self.add_input("electricity_in2", val=0.0, shape_by_conn=True, units="kW")
        self.add_output("electricity_out", val=0.0, copy_shape="electricity_in1", units="kW")

    def compute(self, inputs, outputs):
        outputs["electricity_out"] = inputs["electricity_in1"] + inputs["electricity_in2"]
