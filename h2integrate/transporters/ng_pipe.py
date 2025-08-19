import openmdao.api as om


class NGPipePerformanceModel(om.ExplicitComponent):
    """
    Pass-through pipe with no losses.
    """

    def setup(self):
        self.add_input(
            "natural_gas_in",
            val=0.0,
            shape_by_conn=True,
            copy_shape="natural_gas_out",
            units="MMBtu",
        )
        self.add_output(
            "natural_gas_out",
            val=0.0,
            shape_by_conn=True,
            copy_shape="natural_gas_in",
            units="MMBtu",
        )

    def compute(self, inputs, outputs):
        outputs["natural_gas_out"] = inputs["natural_gas_in"]
