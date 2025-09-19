"""
Pytest configuration file.
"""

import os

from h2integrate.resource.utilities.nrel_developer_api_keys import set_nrel_key_dot_env


def pytest_sessionstart(session):
    # Set a dummy API key
    os.environ["NREL_API_KEY"] = "a" * 40
    set_nrel_key_dot_env()

    # Set RESOURCE_DIR to None so pulls example files from default DIR
    os.environ.pop("RESOURCE_DIR", None)
