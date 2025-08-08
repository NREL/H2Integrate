from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from h2integrate.resource.wind import WindAPI, WindAPIConfig


@pytest.fixture
def open_meteo_config():
    return WindAPIConfig(
        source="open-meteo",
        year=2023,
        height=80,
        latitude=40.0,
        longitude=-105.0,
        turbulence_intensity=0.1,
        elevation=1828,
    )


@pytest.fixture
def nrel_rex_config():
    return WindAPIConfig(
        source="nrel-rex",
        year=2023,
        height=80,
        latitude=40.0,
        longitude=-105.0,
        turbulence_intensity=0.1,
        elevation=1828,
        api_key="test_api_key",
    )


@patch("h2integrate.resource.wind.requests.get")
def test_fetch_open_meteo_data(mock_get, open_meteo_config, subtests):
    # Mock the API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "hourly": {
            "wind_speed": [5.0, 6.0, 7.0],
            "wind_direction": [180.0, 190.0, 200.0],
        }
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Create the WindAPI instance
    wind_api = WindAPI(open_meteo_config)

    # Fetch data
    wind_data = wind_api.fetch_data()

    # Subtests for assertions
    with subtests.test("Check DataFrame structure"):
        assert isinstance(wind_data, pd.DataFrame)
        assert list(wind_data.columns) == ["wind_speed", "wind_direction", "height"]

    with subtests.test("Check wind_speed values"):
        assert wind_data["wind_speed"].tolist() == [5.0, 6.0, 7.0]

    with subtests.test("Check wind_direction values"):
        assert wind_data["wind_direction"].tolist() == [180.0, 190.0, 200.0]

    with subtests.test("Check height values"):
        assert wind_data["height"].tolist() == [80, 80, 80]


@patch("h2integrate.resource.wind.requests.get")
def test_fetch_nrel_rex_data(mock_get, nrel_rex_config, subtests):
    # Mock the API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "outputs": {
            "wind_speed": [4.0, 5.0, 6.0],
            "wind_direction": [170.0, 180.0, 190.0],
        }
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Create the WindAPI instance
    wind_api = WindAPI(nrel_rex_config)

    # Fetch data
    wind_data = wind_api.fetch_data()

    # Subtests for assertions
    with subtests.test("Check DataFrame structure"):
        assert isinstance(wind_data, pd.DataFrame)
        assert list(wind_data.columns) == ["wind_speed", "wind_direction", "height"]

    with subtests.test("Check wind_speed values"):
        assert wind_data["wind_speed"].tolist() == [4.0, 5.0, 6.0]

    with subtests.test("Check wind_direction values"):
        assert wind_data["wind_direction"].tolist() == [170.0, 180.0, 190.0]

    with subtests.test("Check height values"):
        assert wind_data["height"].tolist() == [80, 80, 80]


def test_invalid_source(subtests):
    # Subtest for invalid source
    with subtests.test("Check invalid source raises ValueError"):
        with pytest.raises(ValueError):
            # Create a config with an invalid source
            WindAPIConfig(
                source="invalid-source",
                year=2023,
                height=80,
                latitude=40.0,
                longitude=-105.0,
                turbulence_intensity=0.1,
                elevation=1828,
            )


def test_missing_api_key(subtests):
    # Create a config for NREL REX without an API key

    # Subtest for missing API key
    with subtests.test("Check missing API key raises ValueError"):
        with pytest.raises(ValueError, match="API key is required for NREL REX API."):
            config = WindAPIConfig(
                source="nrel-rex",
                year=2023,
                height=80,
                latitude=40.0,
                longitude=-105.0,
                turbulence_intensity=0.1,
                elevation=1828,
            )

            # Create the WindAPI instance
            wind_api = WindAPI(config)

            # try to fetch data
            wind_api.fetch_data()
