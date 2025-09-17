from h2integrate.core.utilities import CostModelBaseConfig
from h2integrate.core.model_baseclasses import CostModelBaseClass


class IronComponent(CostModelBaseClass):
    """
    A simple OpenMDAO component that represents an Iron model from old GreenHEART code.

    This component uses caching to store and retrieve results of the iron model
    based on the configuration.
    """

    def setup(self):
        self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        config_dict = {
            "cost_year": self.options["tech_config"]["model_inputs"]["cost_parameters"]["cost_year"]
        }
        self.config = CostModelBaseConfig.from_dict(config_dict)
        super().setup()

        self.hopp_config = self.options["tech_config"]["performance_model"]["config"]
