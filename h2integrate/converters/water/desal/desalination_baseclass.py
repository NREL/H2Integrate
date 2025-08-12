import openmdao.api as om


class DesalinationPerformanceBaseClass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_output("water", val=0.0, units="m**3/h", desc="Fresh water")
        self.add_output("mass", val=0.0, units="kg", desc="Mass of desalination system")
        self.add_output("footprint", val=0.0, units="m**2", desc="Footprint of desalination system")

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")


class DesalinationCostBaseClass(om.ExplicitComponent):
    def setup(self):
        super().setup()
        # Inputs for cost model configuration
        self.add_input(
            "plant_capacity_kgph", val=0.0, units="kg/h", desc="Desired freshwater flow rate"
        )


class DesalinationFinanceBaseClass(om.ExplicitComponent):
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
