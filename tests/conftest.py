"""
Pytest configuration file.
"""

import os

from hopp import TEST_ENV_VAR
from hopp.utilities.keys import set_nrel_key_dot_env


def pytest_sessionstart(session):
    os.environ["ENV"] = TEST_ENV_VAR

    # Set a dummy API key
    os.environ["NREL_API_KEY"] = "a" * 40
    set_nrel_key_dot_env()

    # Set RESOURCE_DIR to None so pulls example files from default DIR
    os.environ.pop("RESOURCE_DIR", None)
