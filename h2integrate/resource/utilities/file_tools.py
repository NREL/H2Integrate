import os
from pathlib import Path

from h2integrate import RESOURCE_DEFAULT_DIR


def check_resource_dir(resource_dir=None, resource_subdir=None):
    # check for user-provided resource dir
    if resource_dir is not None:
        if not Path(resource_dir).is_dir():
            Path.mkdir(resource_dir, exist_ok=True)
        if resource_subdir is None:
            return Path(resource_dir)
        resource_full_dir = Path(resource_dir) / resource_subdir
        resource_full_dir = check_resource_dir(resource_dir=resource_full_dir)
        return resource_full_dir

    # Check for user-defined environment variable with resource subdir
    resource_dir = os.getenv("RESOURCE_DIR")
    if resource_dir is not None:
        if not Path(resource_dir).is_dir():
            Path.mkdir(resource_dir, exist_ok=True)
        if resource_subdir is None:
            return Path(resource_dir)
        resource_full_dir = Path(resource_dir) / resource_subdir
        resource_full_dir = check_resource_dir(resource_dir=resource_full_dir)
        return resource_full_dir

    # use default resource directory
    if resource_subdir is None:
        return RESOURCE_DEFAULT_DIR
    resource_full_dir = RESOURCE_DEFAULT_DIR / resource_subdir
    resource_full_dir = check_resource_dir(resource_dir=resource_full_dir)
    return resource_full_dir
