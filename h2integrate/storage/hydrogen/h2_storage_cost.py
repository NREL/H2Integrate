from attrs import field, define
from openmdao.utils import units

from h2integrate.core.utilities import BaseConfig, merge_shared_inputs
from h2integrate.core.validators import contains, range_val
from h2integrate.core.model_baseclasses import CostModelBaseClass


# TODO: fix import structure in future refactor
from h2integrate.simulation.technologies.hydrogen.h2_storage.lined_rock_cavern.lined_rock_cavern import LinedRockCavernStorage  # noqa: E501  # fmt: skip  # isort:skip
from h2integrate.simulation.technologies.hydrogen.h2_storage.salt_cavern.salt_cavern import SaltCavernStorage  # noqa: E501  # fmt: skip  # isort:skip
from h2integrate.simulation.technologies.hydrogen.h2_storage.pipe_storage import UndergroundPipeStorage  # noqa: E501  # fmt: skip  # isort:skip


@define
class HydrogenStorageBaseCostModelConfig(BaseConfig):
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

    def make_model_dict(self):
        params = self.as_dict()
        h2i_params = [
            "max_capacity",
            "max_charge_rate",
            "commodity_name",
            "commodity_units",
            "cost_year",
        ]
        lrc_dict = {k: v for k, v in params.items() if k not in h2i_params}
        return lrc_dict


class HydrogenStorageBaseCostModel(CostModelBaseClass):
    def initialize(self):
        super().initialize()

    def setup(self):
        self.config = HydrogenStorageBaseCostModelConfig.from_dict(
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

        self.add_input(
            "max_capacity",
            val=self.config.max_capacity,
            units=f"{self.config.commodity_units}*h",
            desc="Hydrogen storage capacity",
        )

    def make_storage_input_dict(self, inputs):
        storage_input = {}

        storage_input = self.config.make_model_dict()

        # convert capacity to kg
        max_capacity_kg = units.convert_units(
            inputs["max_capacity"], f"({self.config.commodity_units})*h", "kg"
        )

        # convert charge rate to kg/h
        storage_max_fill_rate = units.convert_units(
            inputs["max_charge_rate"], f"{self.config.commodity_units}", "kg/h"
        )

        storage_input["h2_storage_kg"] = max_capacity_kg[0]

        # below has to be in kg/day
        storage_input["system_flow_rate"] = storage_max_fill_rate[0]

        return storage_input

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        # storage_input = self.make_storage_input_dict(inputs)

        raise NotImplementedError("This method should be implemented in a subclass.")


class LinedRockCavernStorageCostModel(HydrogenStorageBaseCostModel):
    def initialize(self):
        super().initialize()

    def setup(self):
        super().setup()

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        storage_input = self.make_storage_input_dict(inputs)
        h2_storage = LinedRockCavernStorage(storage_input)

        h2_storage.lined_rock_cavern_capex()
        h2_storage.lined_rock_cavern_opex()

        outputs["CapEx"] = h2_storage.output_dict["lined_rock_cavern_storage_capex"]
        outputs["OpEx"] = h2_storage.output_dict["lined_rock_cavern_storage_opex"]


class SaltCavernStorageCostModel(HydrogenStorageBaseCostModel):
    def initialize(self):
        super().initialize()

    def setup(self):
        super().setup()

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        storage_input = self.make_storage_input_dict(inputs)
        h2_storage = SaltCavernStorage(storage_input)

        h2_storage.salt_cavern_capex()
        h2_storage.salt_cavern_opex()

        outputs["CapEx"] = h2_storage.output_dict["salt_cavern_storage_capex"]
        outputs["OpEx"] = h2_storage.output_dict["salt_cavern_storage_opex"]


@define
class PipeStorageCostModelConfig(HydrogenStorageBaseCostModelConfig):
    compressor_output_pressure: float = field(default=100, kw_only=True)  # bar


class PipeStorageCostModel(HydrogenStorageBaseCostModel):
    def initialize(self):
        super().initialize()

    def setup(self):
        super().setup()

        self.config = PipeStorageCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance"),
            strict=False,
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        storage_input = self.make_storage_input_dict(inputs)
        h2_storage = UndergroundPipeStorage(storage_input)

        h2_storage.pipe_storage_capex()
        h2_storage.pipe_storage_opex()

        outputs["CapEx"] = h2_storage.output_dict["pipe_storage_capex"]
        outputs["OpEx"] = h2_storage.output_dict["pipe_storage_opex"]
