import openmdao.api as om


class BatteryPerformanceBaseClass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input(
            "electricity_in",
            val=0.0,
            shape_by_conn=True,
            units="kW",
            desc="Power input to Battery",
        )

        self.add_output(
            "electricity_out",
            val=0.0,
            copy_shape="electricity_in",
            units="kW",
            desc="Total electricity out of Battery",
        )

        self.add_output(
            "SOC",
            val=0.0,
            copy_shape="electricity_in",
            units="percent",
            desc="SOC of Battery",
        )

        self.add_output(
            "battery_electricity_out",
            val=0.0,
            copy_shape="electricity_in",
            units="kW",
            desc="Electricty output from Battery only",
        )

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")
