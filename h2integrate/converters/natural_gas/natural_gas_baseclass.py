import openmdao.api as om


n_timesteps = 8760


class NaturalGasPerformanceBaseClass(om.ExplicitComponent):
    """
    Base class for natural gas plant performance models.

    This base class defines the common interface for natural gas combustion
    turbine (NGCT) and natural gas combined cycle (NGCC) performance models.
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_input(
            "natural_gas_in",
            val=0.0,
            shape=n_timesteps,
            units="MMBtu",
            desc="Natural gas input energy",
        )
        self.add_output(
            "electricity_out",
            val=0.0,
            shape=n_timesteps,
            units="MW",
            desc="Electricity output from natural gas plant",
        )

    def compute(self, inputs, outputs):
        """
        Computation for the OM component.

        For a template class this is not implemented and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")
