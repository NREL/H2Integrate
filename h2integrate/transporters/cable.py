import openmdao.api as om


class CablePerformanceModel(om.ExplicitComponent):
    """
    Pass-through cable with no losses.
    """

    def setup(self):
        self.add_input(
            "electricity_in",
            val=0.0,
            shape_by_conn=True,
            copy_shape="electricity_out",
            units="kW",
        )
        self.add_output(
            "electricity_out",
            val=0.0,
            shape_by_conn=True,
            copy_shape="electricity_in",
            units="kW",
        )

    def compute(self, inputs, outputs):
        outputs["electricity_out"] = inputs["electricity_in"]
