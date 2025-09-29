from pathlib import Path

import openmdao.api as om
from pytest import fixture

from h2integrate import RESOURCE_DEFAULT_DIR
from h2integrate.resource.solar.nrel_developer_goes_api_models import (
    GOESAggregatedNRELDeveloperAPISolarResource,
)


@fixture
def plant_simulation_utc_start():
    plant = {
        "plant_life": 30,
        "simulation": {
            "dt": 3600,
            "n_timesteps": 8760,
            "start_time": "01/01/1900 00:30:00",
            "timezone": 0,
        },
    }
    return plant


@fixture
def site_config():
    site = {
        "latitude": 34.22,
        "longitude": -102.75,
        "resources": {
            "solar_resource": {
                "resource_model": "goes_aggregated_solar_v4_api",
                "resource_parameters": {
                    "latitude": 34.22,
                    "longitude": -102.75,
                    "resource_year": 2012,
                },
            }
        },
    }
    return site


def test_solar_resource_loaded_from_default_dir(plant_simulation_utc_start, site_config, subtests):
    plant_config = {
        "site": site_config,
        "plant": plant_simulation_utc_start,
    }

    prob = om.Problem()
    comp = GOESAggregatedNRELDeveloperAPISolarResource(
        plant_config=plant_config,
        resource_config=plant_config["site"]["resources"]["solar_resource"]["resource_parameters"],
        driver_config={},
    )
    prob.model.add_subsystem("resource", comp)
    prob.setup()
    prob.run_model()
    goes_data = prob.get_val("resource.solar_resource_data")

    solar_dir = RESOURCE_DEFAULT_DIR / "solar"
    with subtests.test("filepath for data was found where expected"):
        assert Path(goes_data["filepath"]).exists()
        assert Path(goes_data["filepath"]).parent == solar_dir

    data_keys = [
        "ghi",
        "dhi",
        "dni",
        "temperature",
        "pressure",
        "dew_point",
        "wind_speed",
        "wind_direction",
    ]
    with subtests.test("resource data is 8760 in length"):
        assert all(len(goes_data[k]) == 8760 for k in data_keys)
