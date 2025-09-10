import openmdao.api as om


class WindPerformanceBaseClass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        self.add_output(
            "electricity_out",
            val=0.0,
            shape=n_timesteps,
            units="kW",
            desc="Power output from WindPlant",
        )
        self.add_discrete_input(
            "wind_resource_data",
            val={},
            desc="Wind resource data dictionary",
        )

    def calculate_bounding_heights_from_resource_data(
        self, hub_height_meters, resource_data, resource_vars=["wind_speed", "wind_direction"]
    ):
        heights_per_parameter = {}
        allowed_hub_height_meters = set()
        for param in resource_vars:
            params_heights = [
                int(k.split("_")[-1].replace("m", "").strip())
                for k, v in resource_data.items()
                if param in k and "m" in k.split("_")[-1]
            ]
            if len(params_heights) > 0:
                heights_per_parameter.update({param: params_heights})
                allowed_hub_height_meters.update(params_heights)
        # NOTE: this assumes that all variables in resource_vars has the same heights
        if any(float(hh) == float(hub_height_meters) for hh in allowed_hub_height_meters):
            return [int(hub_height_meters)]
        heights_lower = [hh for hh in allowed_hub_height_meters if hh / hub_height_meters < 1]
        heights_upper = [hh for hh in allowed_hub_height_meters if hh / hub_height_meters > 1]
        height_low = (
            max(heights_lower) if len(heights_lower) > 0 else min(allowed_hub_height_meters)
        )
        height_high = (
            min(heights_upper) if len(heights_upper) > 0 else max(allowed_hub_height_meters)
        )
        return [int(height_low), int(height_high)]

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """
        Computation for the OM component.

        For a template class this is not implement and raises an error.
        """

        raise NotImplementedError("This method should be implemented in a subclass.")


class WindFinanceBaseClass(om.ExplicitComponent):
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
