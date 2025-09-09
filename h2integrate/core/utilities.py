from typing import Any
from collections import OrderedDict

import attrs
import numpy as np
from attrs import Attribute, field, define


try:
    from pyxdsm.XDSM import FUNC, XDSM
except ImportError:
    pass


def create_xdsm_from_config(config, output_file="connections_xdsm"):
    """
    Create an XDSM diagram from a given plant configuration and save it to a pdf file.

    Parameters
    ----------
    config : dict
        Configuration dictionary containing technology interconnections.
    output_file : str, optional
        The name of the output file where the XDSM diagram will be saved.
    """
    # Create an XDSM object
    x = XDSM(use_sfmath=True)

    # Use an OrderedDict to keep the order of technologies
    technologies = OrderedDict()
    if "technology_interconnections" not in config:
        return

    for conn in config["technology_interconnections"]:
        technologies[conn[0]] = None  # Source
        technologies[conn[1]] = None  # Destination

    # Add systems to the XDSM
    for tech in technologies.keys():
        tech_label = tech.replace("_", r"\_")
        x.add_system(tech, FUNC, rf"\text{{{tech_label}}}")

    # Add connections
    for conn in config["technology_interconnections"]:
        if len(conn) == 3:
            source, destination, data = conn
            connection_label = data
        else:
            source, destination, data, label = conn

        source.replace("_", r"\_")
        destination.replace("_", r"\_")
        connection_label = rf"\text{{{data} {'via'} {label}}}"

        x.connect(source, destination, connection_label)

    # Write the diagram to a file
    x.write(output_file, quiet=True)
    print(f"XDSM diagram written to {output_file}.tex")


def merge_shared_inputs(config, input_type):
    """
    Merges two dictionaries from a configuration object and resolves potential conflicts.

    This function combines the dictionaries associated with `shared_parameters` and
    `performance_parameters`, `cost_parameters`, or `finance_parameters` in the provided
    `config` dictionary. If both dictionaries contain the same keys,
    a ValueError is raised to prevent duplicate parameter definitions.

    Parameters:
        config (dict): A dictionary containing configuration data. It must include keys
                       like `shared_parameters` and `{input_type}_parameters`.
        input_type (str): The type of input parameters to merge. Valid values are
                          'performance', 'control', 'cost', or 'finance'.

    Returns:
        dict: A merged dictionary containing parameters from both `shared_parameters`
              and `{input_type}_parameters`. If one of the dictionaries is missing,
              the function returns the existing dictionary.

    Raises:
        ValueError: If duplicate keys are found in `shared_parameters` and
                    `{input_type}_parameters`.
    """

    if f"{input_type}_parameters" in config.keys() and "shared_parameters" in config.keys():
        common_keys = config[f"{input_type}_parameters"].keys() & config["shared_parameters"].keys()
        if common_keys:
            raise ValueError(
                f"Duplicate parameters found: {', '.join(common_keys)}. "
                f"Please define parameters only once in the shared and {input_type} dictionaries."
            )
        return {**config[f"{input_type}_parameters"], **config["shared_parameters"]}
    elif "shared_parameters" not in config.keys():
        return config[f"{input_type}_parameters"]
    else:
        return config["shared_parameters"]


@define
class BaseConfig:
    """
    A Mixin class to allow for kwargs overloading when a data class doesn't
    have a specific parameter defined. This allows passing of larger dictionaries
    to a data class without throwing an error.
    """

    @classmethod
    def from_dict(cls, data: dict, strict=True):
        """Maps a data dictionary to an `attr`-defined class.

        TODO: Add an error to ensure that either none or all the parameters are passed in

        Args:
            data : dict
                The data dictionary to be mapped.
            strict: bool
                A flag enabling strict parameter processing, meaning that no extra parameters
                    may be passed in or an AttributeError will be raised.
        Returns:
            cls
                The `attr`-defined class.
        """
        # Check for any inputs that aren't part of the class definition
        if strict is True:
            class_attr_names = [a.name for a in cls.__attrs_attrs__]
            extra_args = [d for d in data if d not in class_attr_names]
            if len(extra_args):
                raise AttributeError(
                    f"The initialization for {cls.__name__} was given extraneous "
                    f"inputs: {extra_args}"
                )

        kwargs = {a.name: data[a.name] for a in cls.__attrs_attrs__ if a.name in data and a.init}

        # Map the inputs must be provided: 1) must be initialized, 2) no default value defined
        required_inputs = [
            a.name for a in cls.__attrs_attrs__ if a.init and a.default is attrs.NOTHING
        ]
        undefined = sorted(set(required_inputs) - set(kwargs))

        if undefined:
            raise AttributeError(
                f"The class definition for {cls.__name__} is missing the following inputs: "
                f"{undefined}"
            )
        return cls(**kwargs)

    def as_dict(self) -> dict:
        """Creates a JSON and YAML friendly dictionary that can be save for future reloading.
        This dictionary will contain only `Python` types that can later be converted to their
        proper `Turbine` formats.

        Returns:
            dict: All key, value pairs required for class re-creation.
        """
        return attrs.asdict(self, filter=attr_hopp_filter, value_serializer=attr_serializer)


@define
class CostModelBaseConfig(BaseConfig):
    cost_year: int = field(converter=int)


def attr_serializer(inst: type, field: Attribute, value: Any):
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def attr_hopp_filter(inst: Attribute, value: Any) -> bool:
    if inst.init is False:
        return False
    if value is None:
        return False
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return False
    return True


def check_pysam_input_params(user_dict, pysam_options):
    """Checks for different values provided in two dictionaries that have the general format::

        value = input_dict[group][group_param]

    Args:
        user_dict (dict): top-level performance model inputs formatted to align with
            the corresponding PySAM module.
        pysam_options (dict): additional PySAM module options.

    Raises:
        ValueError: if there are two different values provided for the same key.

    """
    for group, group_params in user_dict.items():
        if group in pysam_options:
            for key in group_params.keys():
                if key in pysam_options:
                    if pysam_options[group][key] != user_dict[group][key]:
                        msg = (
                            f"Inconsistent values provided for parameter {key} in {group} Group."
                            f"pysam_options has value of {pysam_options[group][key]} "
                            f"but user also specified value of {user_dict[group][key]}. "
                        )
                        raise ValueError(msg)
    return


def check_plant_config_and_profast_params(
    plant_config_dict: dict, pf_param_dict: dict, plant_config_key: str, pf_config_key: str
):
    """
    Checks for consistency between values in the plant configuration dictionary and the
    ProFAST parameters dictionary.

    This function compares the value associated with `plant_config_key` in `plant_config_dict`
    to the value associated with `pf_config_key` in `pf_param_dict`. If `pf_config_key` is not
    present in `pf_param_dict`, the value from `plant_config_dict` is used as the default.
    If the values are inconsistent, a ValueError is raised with a descriptive message.

    Args:
        plant_config_dict (dict): Dictionary containing plant configuration parameters.
        pf_param_dict (dict): Dictionary containing ProFAST parameter values.
        plant_config_key (str): Key to look up in `plant_config_dict`.
        pf_config_key (str): Key to look up in `pf_param_dict`.

    Raises:
        ValueError: If the values for the specified keys in the two dictionaries are inconsistent.
    """

    if (
        pf_param_dict.get(pf_config_key, plant_config_dict[plant_config_key])
        != plant_config_dict[plant_config_key]
    ):
        msg = (
            f"Inconsistent values provided for {pf_config_key} and {plant_config_key}, "
            f"{pf_config_key} is {pf_param_dict.get(pf_config_key)} but "
            f"{plant_config_key} is {plant_config_dict[plant_config_key]}."
            f"Please check that {pf_config_key} is the same as {plant_config_key} or remove "
            f"{pf_config_key} from pf_params input."
        )
        raise ValueError(msg)


def dict_to_yaml_formatting(orig_dict):
    """Recursive method to convert arrays to lists and numerical entries to floats.
    This is primarily used before writing a dictionary to a YAML file to ensure
    proper output formatting.

    Args:
        orig_dict (dict): input dictionary

    Returns:
        dict: input dictionary with reformatted values.
    """
    for key, val in orig_dict.items():
        if isinstance(val, dict):
            tmp = dict_to_yaml_formatting(orig_dict.get(key, {}))
            orig_dict[key] = tmp
        else:
            if isinstance(key, list):
                for i, k in enumerate(key):
                    if isinstance(orig_dict[k], (str, bool, int)):
                        orig_dict[k] = orig_dict.get(k, []) + val[i]
                    elif isinstance(orig_dict[k], (list, np.ndarray)):
                        orig_dict[k] = np.array(val, dtype=float).tolist()
                    else:
                        orig_dict[k] = float(val[i])
            elif isinstance(key, str):
                if isinstance(orig_dict[key], (str, bool, int)):
                    continue
                if isinstance(orig_dict[key], (list, np.ndarray)):
                    if any(isinstance(v, dict) for v in val):
                        for vii, v in enumerate(val):
                            if isinstance(v, dict):
                                new_val = dict_to_yaml_formatting(v)
                            else:
                                new_val = v if isinstance(v, (str, bool, int)) else float(v)
                            orig_dict[key][vii] = new_val
                    else:
                        new_val = [v if isinstance(v, (str, bool, int)) else float(v) for v in val]
                        orig_dict[key] = new_val
                else:
                    orig_dict[key] = float(val)
    return orig_dict


def determine_commodity_types_from_technology_names(tech_configs, electricity_producing_techs):
    """Determines the commodity types present in a plant based on the technology names."""

    commodity_types = []

    if "steel" in tech_configs:
        commodity_types.append("steel")
    if "electrolyzer" in tech_configs:
        commodity_types.append("hydrogen")
    if "methanol" in tech_configs:
        commodity_types.append("methanol")
    if "ammonia" in tech_configs:
        commodity_types.append("ammonia")
    if "geoh2" in tech_configs:
        commodity_types.append("hydrogen")
    if "doc" in tech_configs:
        commodity_types.append("co2")
    if "air_separator" in tech_configs:
        commodity_types.append("nitrogen")
    if "oae" in tech_configs:
        commodity_types.append("co2")
    for tech in electricity_producing_techs:
        if tech in tech_configs:
            commodity_types.append("electricity")
            break

    return commodity_types
