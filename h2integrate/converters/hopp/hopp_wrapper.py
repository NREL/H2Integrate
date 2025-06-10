import hashlib
from pathlib import Path

import dill
import numpy as np
import openmdao.api as om

from h2integrate.converters.hopp.hopp_mgmt import run_hopp, setup_hopp


n_timesteps = 8760


class HOPPComponent(om.ExplicitComponent):
    """
    A simple OpenMDAO component that represents a HOPP model.

    This component uses caching to store and retrieve results of the HOPP model
    based on the configuration and project lifetime. The caching mechanism helps
    to avoid redundant computations and speeds up the execution by reusing previously
    computed results when the same configuration is encountered.
    """

    def initialize(self):
        self.options.declare("tech_config", types=dict)
        self.options.declare("plant_config", types=dict)

    def setup(self):
        # Outputs
        self.add_output(
            "electricity_out", val=np.zeros(n_timesteps), units="kW", desc="Power output"
        )
        self.add_output("CapEx", val=0.0, units="USD", desc="Total capital expenditures")
        self.add_output("OpEx", val=0.0, units="USD/year", desc="Total fixed operating costs")

    def compute(self, inputs, outputs):
        # Create a unique hash for the current configuration to use as a cache key
        config_hash = hashlib.md5(
            str(self.options["tech_config"]["performance_model"]["config"]).encode("utf-8")
            + str(self.options["plant_config"]["plant"]["plant_life"]).encode("utf-8")
        ).hexdigest()

        # Define the keys of interest from the HOPP results that we want to cache
        keys_of_interest = [
            "combined_hybrid_power_production_hopp",
            "capex",
            "opex",
        ]

        # Create a cache directory if it doesn't exist
        cache_dir = Path("cache")
        if not cache_dir.exists():
            cache_dir.mkdir(parents=True)
        cache_file = f"cache/{config_hash}.pkl"

        # Check if the results for the current configuration are already cached
        if Path(cache_file).exists():
            # Load the cached results
            cache_path = Path(cache_file)
            with cache_path.open("rb") as f:
                subset_of_hopp_results = dill.load(f)
        else:
            electrolyzer_rating = None
            if "electrolyzer_rating" in self.options["tech_config"]:
                electrolyzer_rating = self.options["tech_config"]["electrolyzer_rating"]

            self.hybrid_interface = setup_hopp(
                self.options["tech_config"]["performance_model"]["config"],
                self.options["plant_config"],
                electrolyzer_rating,
            )

            # Run the HOPP model and get the results
            hopp_results = run_hopp(
                self.hybrid_interface, self.options["plant_config"]["plant"]["plant_life"]
            )
            # Extract the subset of results we are interested in
            subset_of_hopp_results = {key: hopp_results[key] for key in keys_of_interest}
            # Cache the results for future use
            cache_path = Path(cache_file)
            with cache_path.open("wb") as f:
                dill.dump(subset_of_hopp_results, f)

        # Set the outputs from the cached or newly computed results
        outputs["electricity_out"] = subset_of_hopp_results["combined_hybrid_power_production_hopp"]
        outputs["CapEx"] = subset_of_hopp_results["capex"]
        outputs["OpEx"] = subset_of_hopp_results["opex"]
