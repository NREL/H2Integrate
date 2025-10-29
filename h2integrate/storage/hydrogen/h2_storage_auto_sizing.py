import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs


from h2integrate.simulation.technologies.hydrogen.h2_storage.storage_sizing import hydrogen_storage_capacity  # noqa: E501  # fmt: skip  # isort:skip


@define
class H2StorageSizingModelConfig(BaseConfig):
    commodity_name: str = field(default="hydrogen")
    commodity_units: str = field(default="kg")
    electrolyzer_rating_mw_for_h2_storage_sizing: float | None = field(default=None)
    size_capacity_from_demand: dict = field(default={"flag": True})
    capacity_from_max_on_turbine_storage: bool = field(default=False)
    days: int = field(default=0)
    demand_profile: int | float | list | None = field(default=None)


class H2StorageAutoSizingModel(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

        self.options.declare("verbose", types=bool, default=False)

    def setup(self):
        self.config = H2StorageSizingModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=False,
        )

        super().setup()
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        self.add_input(
            "hydrogen_in",
            val=0.0,
            shape_by_conn=True,
            units="kg/h",
        )
        self.add_input(
            "hydrogen_demand_profile",
            units="kg/h",
            val=0.0,
            shape=n_timesteps,
            desc="Hydrogen demand profile timeseries",
        )

        self.add_input("efficiency", val=0.0, desc="Average efficiency of the electrolyzer")

        self.add_output(
            "max_capacity",
            val=0.0,
            shape=1,
            units="kg",
        )

        self.add_output(
            "max_charge_rate",
            val=0.0,
            shape=1,
            units="kg/h",
        )

    def compute(self, inputs, outputs):
        ########### initialize output dictionary ###########

        storage_max_fill_rate = np.max(inputs["hydrogen_in"])

        ########### get hydrogen storage size in kilograms ###########

        ##################### get storage capacity from hydrogen storage demand
        if self.config.size_capacity_from_demand["flag"]:
            if self.config.electrolyzer_rating_mw_for_h2_storage_sizing is None:
                raise (
                    ValueError(
                        "h2 storage input battery_electricity_discharge must be specified \
                                 if size_capacity_from_demand is True."
                    )
                )
            if np.sum(inputs["hydrogen_demand_profile"]) > 0:
                hydrogen_storage_demand = inputs["hydrogen_demand_profile"]
            else:
                hydrogen_storage_demand = np.mean(
                    inputs["hydrogen_in"]
                )  # TODO: update demand based on end-use needs
            results_dict = {
                "Hydrogen Hourly Production [kg/hr]": inputs["hydrogen_in"],
                "Sim: Average Efficiency [%-HHV]": inputs["efficiency"],
            }
            (
                hydrogen_demand_kgphr,
                hydrogen_storage_capacity_kg,
                hydrogen_storage_duration_hr,
                hydrogen_storage_soc,
            ) = hydrogen_storage_capacity(
                results_dict,
                self.config.electrolyzer_rating_mw_for_h2_storage_sizing,
                hydrogen_storage_demand,
            )
            h2_storage_capacity_kg = hydrogen_storage_capacity_kg
            # h2_storage_results["hydrogen_storage_duration_hr"] = hydrogen_storage_duration_hr
            # h2_storage_results["hydrogen_storage_soc"] = hydrogen_storage_soc

        ##################### get storage capacity based on storage days in config
        else:
            storage_hours = self.config.days * 24
            h2_storage_capacity_kg = round(storage_hours * storage_max_fill_rate)

        outputs["max_charge_rate"] = storage_max_fill_rate
        outputs["max_capacity"] = h2_storage_capacity_kg
