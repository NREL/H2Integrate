import numpy as np
from attrs import field, define
from openmdao.utils import units

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains, range_val
from h2integrate.core.model_baseclasses import CostModelBaseClass


@define
class MCHTOLStorageCostModelConfig(BaseConfig):
    max_capacity: float = field()
    max_charge_rate: float = field()
    max_discharge_rate: float = field()
    charge_equals_discharge: bool = field(default=True)

    commodity_name: str = field(default="hydrogen")
    commodity_units: str = field(default="kg/h", validator=contains(["kg/h", "g/h", "t/h"]))

    storage_efficiency: float = field(default=0.9984, validator=range_val(0, 1))
    cost_year: int = field(default=2024, converter=int, validator=contains([2024]))


class MCHTOLStorageCostModel(CostModelBaseClass):
    def initialize(self):
        super().initialize()

    def setup(self):
        self.config = MCHTOLStorageCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost"),
            strict=False,
        )

        super().setup()

        self.add_input(
            "max_charge_rate",
            val=self.config.max_charge_rate,
            units=f"{self.config.commodity_units}",
            desc="Hydrogen storage charge rate",
        )

        if self.config.charge_equals_discharge:
            self.add_input(
                "max_discharge_rate",
                val=self.config.max_charge_rate,
                units=f"{self.config.commodity_units}",
                desc="Hydrogen storage discharge rate",
            )
        else:
            self.add_input(
                "max_discharge_rate",
                val=self.config.max_discharge_rate,
                units=f"{self.config.commodity_units}",
                desc="Hydrogen storage discharge rate",
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

    def calc_cost_value(self, b0, b1, b2, b3, b4):
        """
        Calculate the value of the cost function for the given coefficients.

        Args:
            b0 (float): Coefficient representing the base cost.
            b1 (float): Coefficient for the Hc (hydrogenation capacity) term.
            b2 (float): Coefficient for the Dc (dehydrogenation capacity) term.
            b3 (float): Coefficient for the Ms (maximum storage) term.
            b4 (float): Coefficient for the As (annual hydrogen into storage) term.
        Returns:
            float: The calculated cost value based on the provided coefficients and attributes.

        """
        return b0 + (b1 * self.Hc) + (b2 * self.Dc) + (b3 * self.Ms) + b4 * self.As

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # convert charge rate to kg/d
        storage_max_fill_rate_tpd = units.convert_units(
            inputs["max_charge_rate"], f"{self.config.commodity_units}", "t/d"
        )

        # convert charge rate to kg/d
        if self.config.charge_equals_discharge:
            storage_max_empty_rate_tpd = units.convert_units(
                inputs["max_charge_rate"], f"{self.config.commodity_units}", "t/d"
            )
        else:
            storage_max_empty_rate_tpd = units.convert_units(
                inputs["max_discharge_rate"], f"{self.config.commodity_units}", "t/d"
            )

        hydrogen_storage_soc_kg = units.convert_units(
            inputs["hydrogen_soc"] * inputs["max_capacity"],
            f"({self.config.commodity_units})*h",
            "kg",
        )

        h2_charge_discharge = np.diff(hydrogen_storage_soc_kg, prepend=False)
        h2_charged_idx = np.argwhere(h2_charge_discharge > 0).flatten()
        annual_h2_stored_kg = sum([h2_charge_discharge[i] for i in h2_charged_idx])

        annual_h2_stored_tpy = units.convert_units(
            annual_h2_stored_kg,
            "kg/yr",
            "t/yr",
        )

        h2_storage_capacity_tons = units.convert_units(
            inputs["max_capacity"], f"({self.config.commodity_units})*h", "t"
        )
        # Equation (3): DC = P_avg
        self.Dc = storage_max_fill_rate_tpd[0]

        # Equation (2): HC = P_nameplate - P_avg
        # P_nameplate = self.max_H2_production_kg_pr_hr * 24 / 1e3
        self.Hc = storage_max_empty_rate_tpd[0]

        # Equation (1): AS = sum(curtailed_h2)
        self.As = annual_h2_stored_tpy  # tons/year

        # Defined in paragraph between Equation (2) and (3)
        self.Ms = h2_storage_capacity_tons[0]

        # overnight capital cost coefficients
        occ_coeff = (54706639.43, 147074.25, 588779.05, 20825.39, 10.31)

        #: fixed O&M cost coefficients
        foc_coeff = (3419384.73, 3542.79, 13827.02, 61.22, 0.0)

        #: variable O&M cost coefficients
        voc_coeff = (711326.78, 1698.76, 6844.86, 36.04, 376.31)

        outputs["CapEx"] = self.calc_cost_value(*occ_coeff)
        outputs["OpEx"] = self.calc_cost_value(*foc_coeff)
        outputs["VarOpEx"] = self.calc_cost_value(*voc_coeff)

        # h2_storage = MCHStorage(
        #     max_H2_production_kg_pr_hr=storage_max_fill_rate[0],
        #     hydrogen_storage_capacity_kg=max_capacity_kg[0],
        #     hydrogen_demand_kg_pr_hr=hydrogen_demand_kgphr,
        #     annual_hydrogen_stored_kg_pr_yr=annual_h2_stored,
        # )

        # h2_storage_costs = h2_storage.run_costs()

        # outputs["CapEx"] = h2_storage_costs["mch_capex"]
        # outputs["OpEx"] = h2_storage_costs["mch_opex"]
        # outputs["VarOpEx"] = h2_storage_costs["mch_variable_om"]
