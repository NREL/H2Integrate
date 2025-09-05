import openmdao.api as om


class PipePerformanceModel(om.ExplicitComponent):
    """
    Pass-through pipe with no losses.
    """

    def initialize(self):
        self.options.declare(
            "transport_item", values=["hydrogen", "co2", "methanol", "ammonia", "nitrogen"]
        )

    def setup(self):
        self.input_name = self.options["transport_item"] + "_in"
        self.output_name = self.options["transport_item"] + "_out"
        self.add_input(
            self.input_name,
            val=0.0,
            shape_by_conn=True,
            copy_shape=self.output_name,
            units="kg/s",
        )
        self.add_output(
            self.output_name,
            val=0.0,
            shape_by_conn=True,
            copy_shape=self.input_name,
            units="kg/s",
        )

    def compute(self, inputs, outputs):
        outputs[self.output_name] = inputs[self.input_name]
