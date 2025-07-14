import numpy as np
import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import range_val


@define
class SimpleASUPerformanceConfig(BaseConfig):
    # energy_demand: float = field()

    size_from_N2_demand: bool = field()
    # turndown_ratio: float = field(default = 0.3, validator=range_val(0,0.9))
    rated_N2_kg_pr_hr: float | None = field(default=None)
    ASU_rated_power_kW: float | None = field(default=None)

    N2_fraction_in_air: float = field(default=78.11)
    O2_fraction_in_air: float = field(default=20.96)
    Ar_fraction_in_air: float = field(default=0.93)
    efficiency_kWh_pr_kg_N2: float = field(default=0.29, validator=range_val(0.119, 0.30))
    # 0.29 is efficiency of pressure swing absorption
    # 0.119 is efficiency of cryogenic

    def __attrs_post_init__(self):
        if self.size_from_N2_demand:
            return
        if self.rated_N2_kg_pr_hr is None and self.ASU_rated_power_kW is None:
            msg = (
                "Either rated_N2_kg_pr_hr or ASU_rated_power_kW must be input if "
                "size_from_N2_demand is False"
            )
            raise ValueError(msg)
        else:
            return


class SimpleASUPerformanceModel(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)
        self.N2_molar_mass = 28.0134  # grams/mol
        self.O2_molar_mass = 15.999  # grams/mol
        self.Ar_molar_mass = 39.948  # grams/mol

    def setup(self):
        self.config = SimpleASUPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        if self.config.size_from_N2_demand:
            shp_cpy = "nitrogen_in"
            self.add_input(
                "nitrogen_in",
                shape=8760,
                # val=0.0,
                # shape_by_conn=True, copy_shape="nitrogen_out",
                units="kg/h",
            )
            self.add_output(
                "electricity_in", val=0.0, shape_by_conn=True, copy_shape=shp_cpy, units="kW"
            )

        else:
            shp_cpy = "electricity_in"
            self.add_input(
                "electricity_in",
                shape=8760,
                # val=0.0,
                # shape_by_conn=True, copy_shape="nitrogen_out",
                units="kW",
            )

        self.add_output("air_in", val=0.0, shape_by_conn=True, copy_shape=shp_cpy, units="kg/h")
        self.add_output("ASU_capacity_kW", val=0.0, units="kW", desc="ASU rated capacity in kW")
        self.add_output(
            "rated_N2_kg_pr_hr", val=0.0, units="kg/h", desc="ASU rated capacity in kg-N2/hour"
        )

        self.add_output(
            "annual_electricity_consumption",
            val=0.0,
            units="kW",
            desc="ASU annual electricity consumption in kWh/year",
        )
        self.add_output(
            "annual_nitrogen_production",
            val=0.0,
            units="kg/year",
            desc="ASU annual nitrogen production in kg-N2/year",
        )
        self.add_output(
            "annual_max_nitrogen_production",
            val=0.0,
            units="kg/year",
            desc="ASU maximum annual nitrogen production in kg-N2/year",
        )
        self.add_output(
            "nitrogen_production_capacity_factor",
            val=0.0,
            units=None,
            desc="ASU annual nitrogen production in kg-N2/year",
        )

        self.add_output(
            "nitrogen_out", val=0.0, shape_by_conn=True, copy_shape=shp_cpy, units="kg/h"
        )

        self.add_output("oxygen_out", val=0.0, shape_by_conn=True, copy_shape=shp_cpy, units="kg/h")

        self.add_output("argon_out", val=0.0, shape_by_conn=True, copy_shape=shp_cpy, units="kg/h")

    def compute(self, inputs, outputs):
        if self.config.size_from_N2_demand:
            rated_N2_kg_pr_hr = np.max(inputs["nitrogen_in"])
            n2_profile_in_kg = inputs["nitrogen_in"]
            ASU_rated_power_kW = rated_N2_kg_pr_hr * self.config.efficiency_kWh_pr_kg_N2
        else:
            n2_profile_in_kg = inputs["electricity_in"] / self.config.efficiency_kWh_pr_kg_N2
            provided_kW_not_kg = (
                self.config.ASU_rated_power_kW is not None and self.config.rated_N2_kg_pr_hr is None
            )
            provided_kg_not_kW = (
                self.config.ASU_rated_power_kW is None and self.config.rated_N2_kg_pr_hr is not None
            )
            provided_both = (
                self.config.ASU_rated_power_kW is not None
                and self.config.rated_N2_kg_pr_hr is not None
            )
            if provided_kW_not_kg:
                rated_N2_kg_pr_hr = (
                    self.config.ASU_rated_power_kW / self.config.efficiency_kWh_pr_kg_N2
                )
                ASU_rated_power_kW = self.config.ASU_rated_power_kW
            if provided_kg_not_kW:
                rated_N2_kg_pr_hr = self.config.rated_N2_kg_pr_hr
                ASU_rated_power_kW = (
                    self.config.rated_N2_kg_pr_hr * self.config.efficiency_kWh_pr_kg_N2
                )
            if provided_both:
                rated_N2_kg_pr_hr = self.config.rated_N2_kg_pr_hr
                ASU_rated_power_kW = self.config.ASU_rated_power_kW
                if ASU_rated_power_kW / rated_N2_kg_pr_hr != self.config.efficiency_kWh_pr_kg_N2:
                    msg = (
                        f"User defined size for ASU system ({ASU_rated_power_kW} kg N2/hour at "
                        f"{rated_N2_kg_pr_hr} kW) has an efficiency of "
                        f"{ASU_rated_power_kW/rated_N2_kg_pr_hr} kWh/kg-N2, this does not "
                        f"match the ASU efficiency of {self.config.efficiency_kWh_pr_kg_N2}"
                    )
                    raise ValueError(msg)

        air_molar_mass = (
            (self.N2_molar_mass * self.config.N2_fraction_in_air / 100)
            + (self.O2_molar_mass * self.config.O2_fraction_in_air / 100)
            + (self.Ar_molar_mass * self.config.Ar_fraction_in_air / 100)
        )

        # NOTE: here is where any operational constraints would be applied to limit the N2 output
        n2_profile_out_kg = np.where(
            n2_profile_in_kg > rated_N2_kg_pr_hr, rated_N2_kg_pr_hr, n2_profile_in_kg
        )

        n2_profile_out_mol = n2_profile_out_kg * 1e3 / self.N2_molar_mass
        air_profile_mol = n2_profile_out_mol / (self.config.N2_fraction_in_air / 100)
        o2_profile_mol = air_profile_mol * (self.config.O2_fraction_in_air / 100)
        ar_profile_mol = air_profile_mol * (self.config.Ar_fraction_in_air / 100)

        air_profile_kg = air_profile_mol * air_molar_mass / 1e3
        o2_profile_kg = o2_profile_mol * self.O2_molar_mass / 1e3
        ar_profile_kg = ar_profile_mol * self.Ar_molar_mass / 1e3

        electricity_kWh = n2_profile_out_kg * self.config.efficiency_kWh_pr_kg_N2
        max_annual_N2 = rated_N2_kg_pr_hr * len(n2_profile_out_kg)
        outputs["rated_N2_kg_pr_hr"] = rated_N2_kg_pr_hr
        outputs["ASU_capacity_kW"] = ASU_rated_power_kW
        outputs["air_in"] = air_profile_kg
        outputs["oxygen_out"] = o2_profile_kg
        outputs["argon_out"] = ar_profile_kg
        outputs["nitrogen_out"] = n2_profile_out_kg
        outputs["nitrogen_production_capacity_factor"] = sum(n2_profile_out_kg) / max_annual_N2
        outputs["annual_nitrogen_production"] = sum(n2_profile_out_kg)
        outputs["annual_max_nitrogen_production"] = max_annual_N2
        outputs["annual_electricity_consumption"] = sum(electricity_kWh)

        if self.config.size_from_N2_demand:
            outputs["electricity_in"] = electricity_kWh
