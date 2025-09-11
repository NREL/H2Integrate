import os
from pathlib import Path

from h2integrate import RESOURCE_DEFAULT_DIR


def check_resource_dir(resource_dir=None, resource_subdir=None):
    """Checks for a folder to contain resource files, or creates one if necessary.
    If `resource_dir` is input, the logic is as follows:

    1) Check that resource_dir exists, if it doesn't, then create a folder.

        Note: If resource_dir is a relative filepath, it is assumed relative to the
        current working directory.

    2) If `resource_subdir` is None, then return the full path `resource_dir`.
        Otherwise, calls this function again with

        >>> check_resource_dir(resource_dir=str(resource_dir / resource_subdir))

    If `resource_dir` is not input, the logic is as follows:

    3) Check for an environment variable named `RESOURCE_DIR`.
        If this environment variable exists, follow the logic in Steps 1-2.

    4) Use RESOURCE_DEFAULT_DIR as the resource_dir and follow the logic in Steps 1-2.

    Args:
        resource_dir (Path | str, optional): Path of directory that has resource files.
             Defaults to None.
        resource_subdir (str, optional): folder name within ``resource_dir``.
            Defaults to None.

    Returns:
        Path: valid directory to save resource files to or load resource files from.
    """

    # check for user-provided resource dir
    if resource_dir is not None:
        if not Path(resource_dir).is_dir():
            Path.mkdir(resource_dir, exist_ok=True)
        if resource_subdir is None:
            if os.getenv("GITHUB_ACTIONS") == "true":
                return Path(resource_dir)
            else:
                return Path(resource_dir).absolute()
        resource_full_dir = Path(resource_dir) / resource_subdir
        resource_full_dir = check_resource_dir(resource_dir=resource_full_dir)
        if os.getenv("GITHUB_ACTIONS") == "true":
            return resource_full_dir
        else:
            return resource_full_dir.absolute()

    # Check for user-defined environment variable with resource subdir
    resource_dir = os.getenv("RESOURCE_DIR")
    if resource_dir is not None:
        if not Path(resource_dir).is_dir():
            Path.mkdir(resource_dir, exist_ok=True)
        if resource_subdir is None:
            if os.getenv("GITHUB_ACTIONS") == "true":
                return Path(resource_dir)
            else:
                return Path(resource_dir).absolute()
        resource_full_dir = Path(resource_dir) / resource_subdir
        resource_full_dir = check_resource_dir(resource_dir=resource_full_dir)
        if os.getenv("GITHUB_ACTIONS") == "true":
            return resource_full_dir
        else:
            return resource_full_dir.absolute()

    # use default resource directory
    if resource_subdir is None:
        return RESOURCE_DEFAULT_DIR
    resource_full_dir = RESOURCE_DEFAULT_DIR / resource_subdir
    resource_full_dir = check_resource_dir(resource_dir=resource_full_dir)
    if os.getenv("GITHUB_ACTIONS") == "true":
        return resource_full_dir
    else:
        return resource_full_dir.absolute()
