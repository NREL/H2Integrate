import os
from pathlib import Path

from dotenv import load_dotenv

from h2integrate import ROOT_DIR


developer_nrel_gov_key = ""
developer_nrel_gov_email = ""


def set_developer_nrel_gov_key(key: str):
    """Set `key` as the global variable `developer_nrel_gov_key`.

    Args:
        key (str): API key for NREL Developer Network. Should be length 40.
    """
    global developer_nrel_gov_key
    developer_nrel_gov_key = key


def set_developer_nrel_gov_email(email: str):
    """Set `email` as the global variable `developer_nrel_gov_email`.

    Args:
        email (str): email corresponding to the API key for NREL Developer Network.
    """
    global developer_nrel_gov_email
    developer_nrel_gov_email = email


def load_file_with_variables(fpath, variables=["NREL_API_KEY", "NREL_API_EMAIL"]):
    """Load environment variables from a text file.

    Args:
        fpath (str | Path): filepath to a text file with the extension '.env' that
            may contain the environment variable(s) in `variables`.
        variables (list | str, optional): environment variable(s) to load from file.
            Defaults to ["NREL_API_KEY", "NREL_API_EMAIL"].

    Raises:
        ValueError: If an environment variable is not found or found multiple times in the file.
    """

    # open the file and read the lines
    with Path(fpath).open("r") as f:
        lines = f.readlines()
    if isinstance(variables, str):
        variables = [variables]

    # interate through each variable
    for var in variables:
        # find a line containing the environment variable
        line_w_var = [line for line in lines if var in line]
        if len(line_w_var) != 1:
            raise ValueError(
                f"{var} variable in found in {fpath} file {len(line_w_var)} times. "
                "Please specify this variable once."
            )
        # grab the line containing the variable,
        # assumes the line containing the variable is formatted as "variable=variable_value"
        val = line_w_var[0].split(f"{var}=").strip()
        # if var is NREL_API_KEY, set it as a global variable
        if var == "NREL_API_KEY":
            set_developer_nrel_gov_key(val)
        # if var is NREL_API_EMAIL, set it as a global variable
        if var == "NREL_API_EMAIL":
            set_developer_nrel_gov_email(val)
    return


def set_nrel_key_dot_env(path=None):
    """Sets the environment variables NREL_API_EMAIL and NREL_API_KEY from a .env file.
    The following logic is used if `path` is input and exists:

    1) If the filename of the path is '.env', load the environment variables using `load_dotenv()`.
        Proceed to Step 3.
    2) If the filename of the path has an extension of '.env' (such a filename of 'my_env.env'),
        then load the environment variables using `load_file_with_variables()`. Proceed to step 3.

    The following logic is used if `path` is not input or does not exist:

    1) check for possible locations of the '.env' file. Searches the current working directory,
        the ROOT_DIR, and the paret of the ROOT_DIR. If the '.env' file is found in one of these
        locations, load the environment variables using `load_dotenv()`. Proceed to step 3.

    The following is run after the above step(s):

    3) Get the environment variables NREL_API_KEY and NREL_API_EMAIL. If the NREL_API_KEY
        variable exists, then set it as a global variable using `set_developer_nrel_gov_key()`.
        If the NREL_API_EMAiL variable exists, then set it as a global variable using
        `set_developer_nrel_gov_email()`.

    Args:
        path (Path | str, optional): Path to environment file.
            Defaults to None.
    """
    if path and Path(path).exists():
        if Path(path).name == ".env":
            load_dotenv(path)
        if Path(path).suffix == ".env":
            NREL_API_KEY = load_file_with_variables(path, variables="NREL_API_KEY")
            NREL_API_EMAIL = load_file_with_variables(path, variables="NREL_API_EMAIL")
    else:
        possible_locs = [Path.cwd() / ".env", ROOT_DIR / ".env", ROOT_DIR.parent / ".env"]
        for r in possible_locs:
            if Path(r).exists():
                load_dotenv(r)
    NREL_API_KEY = os.getenv("NREL_API_KEY")
    NREL_API_EMAIL = os.getenv("NREL_API_EMAIL")
    if NREL_API_KEY is not None:
        set_developer_nrel_gov_key(NREL_API_KEY)
    if NREL_API_EMAIL is not None:
        set_developer_nrel_gov_email(NREL_API_EMAIL)


def get_nrel_developer_api_key(env_path=None):
    """Load the NREL_API_KEY. This method does the following:

    1) check for NREL_API_KEY environment variable, return if found. Otherwise, proceed to Step 2.
    2) check if NREL_API_KEY has already been set as a global variable from
        running `set_nrel_key_dot_env()`. If NREL_API_KEY has not been set, proceed to Step 3.
    3) Attempt to set the NREL_API_KEY by calling `set_nrel_key_dot_env()`.
    4) Check if NREL_API_KEY has been set as a global variable. If found, return.
        Otherwise, raises a ValueError.

    Args:
        env_path (Path | str, optional): Filepath to .env file.
            Defaults to None.

    Raises:
        ValueError: If NREL_API_KEY was not found as an environment variable
            and the path to the environment file was not input.
        ValueError: If NREL_API_KEY was not found as an environment variable and not
            set properly using the environment path.

    Returns:
        str: API key for NREL Developer Network.
    """
    if os.getenv("NREL_API_KEY") is not None:
        return os.getenv("NREL_API_KEY")
    global developer_nrel_gov_key
    if developer_nrel_gov_key is None:
        if env_path is None:
            raise ValueError("NREL_API_KEY has not be set.")
        set_nrel_key_dot_env(path=env_path)
    if developer_nrel_gov_key is None:
        raise ValueError("NREL_API_KEY has not been set")
    return developer_nrel_gov_key


def get_nrel_developer_api_email(env_path=None):
    """Load the NREL_API_EMAIL. This method does the following:

    1) check for NREL_API_EMAIL environment variable, return if found. Otherwise, proceed to Step 2.
    2) check if NREL_API_EMAIL has already been set as a global variable from running
        `set_nrel_key_dot_env()`. If NREL_API_EMAIL has not been set, proceed to Step 3.
    3) Attempt to set the NREL_API_EMAIL by calling `set_nrel_key_dot_env()`.
    4) Check if NREL_API_EMAIL has been set as a global variable. If found, return.
        Otherwise, raises a ValueError.

    Args:
        env_path (Path | str, optional): Filepath to .env file.
            Defaults to None.

    Raises:
        ValueError: If NREL_API_EMAIL was not found as an environment variable
            and the path to the environment file was not input.
        ValueError: If NREL_API_EMAIL was not found as an environment variable and not
            set properly using the environment path.

    Returns:
        str: API key for NREL Developer Network.
    """
    if os.getenv("NREL_API_EMAIL") is not None:
        return os.getenv("NREL_API_EMAIL")
    global developer_nrel_gov_email
    if developer_nrel_gov_email is None:
        if env_path is None:
            raise ValueError("NREL_API_EMAIL has not be set.")
        set_nrel_key_dot_env(path=env_path)
    if developer_nrel_gov_email is None:
        raise ValueError("NREL_API_EMAIL has not been set")
    return developer_nrel_gov_email
