import openmdao.api as om


class PyomoDispatchBaseClass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.add_discrete_output("_create_port", val=None, desc="pyomo port creation function")
        self.add_discrete_output(
            "_create_variables", val=None, desc="pyomo variable creation function"
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """
        Return the Pyomo model elements for a given technology through the OpenMDAO
        infrastructure.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")

    def _create_variables(self, hybrid):
        """Create technology Pyomo variables to add to the Pyomo hybrid plant instance.

        Args:
            hybrid: Pyomo Hybrid plant instance.

        Returns:
            tuple: Tuple containing created variables.
                - generation: Generation from given technology.
                - load: Load from given technology.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")

    def _create_port(self, hybrid):
        """Create technology Pyomo port to add to the Pyomo hybrid plant instance.

        Args:
            hybrid: Hybrid plant instance.

        Returns:
            Port: technology Pyomo Port object.

        """

        raise NotImplementedError("This method should be implemented in a subclass.")
