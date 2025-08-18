import openmdao.api as om


n_timesteps = 8760


class BatteryPerformanceBaseClass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input(
            "electricity_in",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Power input to Battery",
        )

        self.add_output(
            "electricity_out",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Power output from Battery",
        )

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")


class BatteryCostBaseClass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        # Define outputs: CapEx and OpEx costs
        self.add_output("CapEx", val=0.0, units="USD", desc="Capital expenditure")
        self.add_output("OpEx", val=0.0, units="USD/year", desc="Operational expenditure")

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")


class BatteryFinanceBaseClass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input("CapEx", val=0.0, units="USD")
        self.add_input("OpEx", val=0.0, units="USD/year")
        self.add_output("NPV", val=0.0, units="USD", desc="Net present value")

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")
