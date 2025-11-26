from pathlib import Path

from attrs import field, define
from turbine_models.tools.library_tools import check_turbine_library_for_turbine
from turbine_models.tools.interface_tools import get_pysam_turbine_specs, get_floris_turbine_specs

from h2integrate import H2I_LIBRARY_DIR
from h2integrate.core.utilities import BaseConfig, get_path, write_yaml_readable


def export_turbine_to_pysam_format(
    turbine_name, output_folder: Path | str | None = None, output_filename: str | None = None
):
    for group in ["distributed", "offshore", "onshore"]:
        is_valid = check_turbine_library_for_turbine(turbine_name, turbine_group=group)
        if is_valid:
            break
    if not is_valid:
        msg = (
            f"Turbine {turbine_name} was not found in the turbine-models library. "
            "For a list of available turbine names, run `print_turbine_name_list()` method "
            "available in `turbine_models.tools.library_tools`."
        )
        raise ValueError(msg)
    if output_folder is None:
        output_folder = H2I_LIBRARY_DIR
    else:
        output_folder = get_path(output_folder)

    if output_filename is None:
        output_filename = f"pysam_options_{turbine_name}.yaml"

    output_filepath = output_folder / output_filename

    turbine_specs = get_pysam_turbine_specs(turbine_name)

    pysam_options = {"Turbine": turbine_specs}

    write_yaml_readable(pysam_options, output_filepath)

    return output_filepath


@define
class FlorisTurbineDefaults(BaseConfig):
    TSR: float | int = field(default=8.0)
    ref_air_density: float | int = field(default=1.225)
    ref_tilt: float | int = field(default=5.0)
    cosine_loss_exponent_yaw: float | int = field(default=1.88)
    cosine_loss_exponent_tilt: float | int = field(default=1.88)

    def power_thrust_defaults(self):
        d = self.as_dict()
        power_thrust_variables = {k: v for k, v in d.items() if k != "TSR"}
        return power_thrust_variables


def export_turbine_to_floris_format(
    turbine_name,
    output_folder: Path | str | None = None,
    output_filename: str | None = None,
    floris_defaults: dict | FlorisTurbineDefaults = FlorisTurbineDefaults(),
):
    if isinstance(floris_defaults, dict):
        floris_defaults = FlorisTurbineDefaults.from_dict(floris_defaults)
    for group in ["distributed", "offshore", "onshore"]:
        is_valid = check_turbine_library_for_turbine(turbine_name, turbine_group=group)
        if is_valid:
            break
    if not is_valid:
        msg = (
            f"Turbine {turbine_name} was not found in the turbine-models library. "
            "For a list of available turbine names, run `print_turbine_name_list()` method "
            "available in `turbine_models.tools.library_tools`."
        )
        raise ValueError(msg)
    if output_folder is None:
        output_folder = H2I_LIBRARY_DIR
    else:
        output_folder = get_path(output_folder)

    if output_filename is None:
        output_filename = f"floris_turbine_{turbine_name}.yaml"

    output_filepath = output_folder / output_filename

    turbine_specs = get_floris_turbine_specs(turbine_name)

    # add in default values
    if turbine_specs.get("TSR", None) is None:
        turbine_specs.update({"TSR": floris_defaults.TSR})

    power_thrust_defaults = floris_defaults.power_thrust_defaults()
    for var, default_val in power_thrust_defaults.items():
        if turbine_specs["power_thrust_table"].get(var, None) is None:
            turbine_specs["power_thrust_table"].update({var: default_val})

    write_yaml_readable(turbine_specs, output_filepath)

    return output_filepath
