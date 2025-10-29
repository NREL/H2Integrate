import numpy as np
from attrs import field, define
from openmdao.utils import units

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains
from h2integrate.core.model_baseclasses import CostModelBaseClass
from h2integrate.simulation.technologies.hydrogen.h2_storage.mch.mch_cost import MCHStorage


@define
class MCHTOLStorageCostModelConfig(BaseConfig):
    max_capacity: float = field()
    max_charge_rate: float = field()
    compressor_output_pressure: float = field(default=100)  # bar

    commodity_name: str = field(default="hydrogen")
    commodity_units: str = field(default="kg/h", validator=contains(["kg/h", "g/h", "t/h"]))

    cost_year: int = field(default=2024, converter=int, validator=contains([2024]))


class MCHTOLStorageCostModel(CostModelBaseClass):
    def initialize(self):
        super().initialize()

    def setup(self):
        self.config = MCHTOLStorageCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=False,
        )

        super().setup()

        self.add_input(
            "max_charge_rate",
            val=self.config.max_charge_rate,
            units=f"{self.config.commodity_units}",
            desc="Hydrogen storage charge rate",
        )

        self.add_input(
            "max_capacity",
            val=self.config.max_capacity,
            units=f"{self.config.commodity_units}*h",
            desc="Hydrogen storage capacity",
        )

        self.n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        self.add_input(
            "hydrogen_soc",
            units="unitless",
            val=0.0,
            shape=self.n_timesteps,
            desc="Hydrogen state of charge timeseries for storage",
        )
        self.add_input(
            "hydrogen_out",
            val=0.0,
            shape=self.n_timesteps,
            units=f"{self.config.commodity_units}",
            desc="Hydrogen output timeseries from plant after storage including \
            stored and pass-through commodity amounts up to the demand amount",
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # convert capacity to kg
        max_capacity_kg = units.convert_units(
            inputs["max_capacity"], f"({self.config.commodity_units})*h", "kg"
        )

        # convert charge rate to kg/d
        storage_max_fill_rate = units.convert_units(
            inputs["max_charge_rate"], f"{self.config.commodity_units}", "kg/h"
        )

        hydrogen_storage_soc = units.convert_units(
            inputs["hydrogen_soc"] * inputs["max_capacity"],
            f"({self.config.commodity_units})*h",
            "kg",
        )

        hydrogen_from_storage_kg = units.convert_units(
            inputs["hydrogen_out"], f"{self.config.commodity_units}", "kg/h"
        )

        hydrogen_demand_kgphr = np.mean(hydrogen_from_storage_kg)

        h2_charge_discharge = np.diff(hydrogen_storage_soc, prepend=False)
        h2_charged_idx = np.argwhere(h2_charge_discharge > 0).flatten()
        annual_h2_stored = sum([h2_charge_discharge[i] for i in h2_charged_idx])

        h2_storage = MCHStorage(
            max_H2_production_kg_pr_hr=storage_max_fill_rate[0],
            hydrogen_storage_capacity_kg=max_capacity_kg[0],
            hydrogen_demand_kg_pr_hr=hydrogen_demand_kgphr,
            annual_hydrogen_stored_kg_pr_yr=annual_h2_stored,
        )
        h2_storage_costs = h2_storage.run_costs()

        outputs["CapEx"] = h2_storage_costs["mch_capex"]
        outputs["OpEx"] = h2_storage_costs["mch_opex"]
        outputs["VarOpEx"] = h2_storage_costs["mch_variable_om"]
