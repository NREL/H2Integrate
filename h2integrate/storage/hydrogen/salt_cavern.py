from attrs import field, define
from openmdao.utils import units

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains, range_val
from h2integrate.core.model_baseclasses import CostModelBaseClass


# TODO: fix import structure in future refactor
from h2integrate.simulation.technologies.hydrogen.h2_storage.salt_cavern.salt_cavern import SaltCavernStorage  # noqa: E501  # fmt: skip  # isort:skip


@define
class SaltCavernStorageCostModelConfig(BaseConfig):
    max_capacity: float = field()
    max_charge_rate: float = field()

    commodity_name: str = field(default="hydrogen")
    commodity_units: str = field(default="kg/h", validator=contains(["kg/h", "g/h", "t/h"]))

    model: str = field(
        default="papadias",
        converter=(str.strip, str.lower),
        validator=contains(["hdsam", "papadias"]),
    )
    cost_year: int = field(default=2018, converter=int, validator=contains([2018]))
    labor_rate: float = field(default=37.39817, validator=range_val(0, 100))
    insurance: float = field(default=0.01, validator=range_val(0, 1))
    property_taxes: float = field(default=0.01, validator=range_val(0, 1))
    licensing_permits: float = field(default=0.001, validator=range_val(0, 1))
    compressor_om: float = field(default=0.04, validator=range_val(0, 1))
    facility_om: float = field(default=0.01, validator=range_val(0, 1))

    def make_sc_dict(self):
        params = self.as_dict()
        h2i_params = [
            "max_capacity",
            "max_charge_rate",
            "commodity_name",
            "commodity_units",
            "cost_year",
        ]
        lrc_dict = {k: v for k, v in params if k not in h2i_params}
        return lrc_dict


class SaltCavernStorageCostModel(CostModelBaseClass):
    def initialize(self):
        super().initialize()

    def setup(self):
        self.config = SaltCavernStorageCostModelConfig.from_dict(
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

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        storage_input = {}

        storage_input = self.config.make_sc_dict()

        # convert capacity to kg
        max_capacity_kg = units.convert_units(
            inputs["max_capacity"], f"({self.config.commodity_units})*h", "kg"
        )

        # convert charge rate to kg/d
        storage_max_fill_rate = units.convert_units(
            inputs["max_charge_rate"], f"{self.config.commodity_units}", "kg/d"
        )

        storage_input["h2_storage_kg"] = max_capacity_kg[0]

        # below has to be in kg/day
        storage_input["system_flow_rate"] = storage_max_fill_rate[0]

        # run salt cavern storage model
        h2_storage = SaltCavernStorage(storage_input)

        h2_storage.salt_cavern_capex()
        h2_storage.salt_cavern_opex()

        outputs["CapEx"] = h2_storage.output_dict["salt_cavern_storage_capex"]
        outputs["OpEx"] = h2_storage.output_dict["salt_cavern_storage_opex"]
