import openmdao.api as om


class PipePerformanceModel(om.ExplicitComponent):
    """
    Pass-through pipe with no losses.
    """

    def setup(self):
        self.add_input(
            "hydrogen_in",
            val=0.0,
            shape_by_conn=True,
            copy_shape="hydrogen_out",
            units="kg/s",
        )
        self.add_output(
            "hydrogen_out",
            val=0.0,
            shape_by_conn=True,
            copy_shape="hydrogen_in",
            units="kg/s",
        )

    def compute(self, inputs, outputs):
        outputs["hydrogen_out"] = inputs["hydrogen_in"]
