import os
from pathlib import Path

from dotenv import load_dotenv

from h2integrate import ROOT_DIR


developer_nrel_gov_key = ""
developer_nrel_gov_email = ""


def set_developer_nrel_gov_key(key: str):
    global developer_nrel_gov_key
    developer_nrel_gov_key = key


def set_developer_nrel_gov_email(email: str):
    global developer_nrel_gov_email
    developer_nrel_gov_email = email


def load_file_with_variables(fpath, variables=["NREL_API_KEY", "NREL_API_EMAIL"]):
    with Path(fpath).open("r") as f:
        lines = f.readlines()
    if isinstance(variables, str):
        variables = [variables]
    for var in variables:
        line_w_var = [line for line in lines if var in line]
        if len(line_w_var) != 1:
            raise ValueError(
                f"{var} variable in found in {fpath} file {len(line_w_var)} times. "
                "Please specify this variable once."
            )
        val = line_w_var[0].split(f"{var}=").strip()
        if var == "NREL_API_KEY":
            set_developer_nrel_gov_key(val)
        if var == "NREL_API_EMAIL":
            set_developer_nrel_gov_email(val)
    return


def set_nrel_key_dot_env(path=None):
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
