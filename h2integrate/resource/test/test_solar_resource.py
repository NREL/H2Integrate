import openmdao.api as om

from h2integrate import EXAMPLE_DIR
from h2integrate.resource.solar import SolarResource


def test_solar_resouce_from_filepath_local_tz(subtests):
    example_folder = EXAMPLE_DIR / "02_texas_ammonia"

    solar_fpath = (
        example_folder / "tech_inputs" / "weather" / "solar" / "32.31714_-100.18_psmv3_60_2013.csv"
    )
    site_config = {
        "latitude": 32.31714,
        "longitude": -100.18,
        "resources": {
            "solar_resource": {
                "resource_year": 2013,
                "interval": 60,
                "resource_origin": "API",
                "resource_filepath": str(solar_fpath),
            }
        },
    }
    config = {"site": site_config}

    prob = om.Problem()
    comp = SolarResource(
        plant_config=config,
        tech_config={},
        driver_config={},
    )

    prob.model.add_subsystem("solar", comp)
    prob.setup()
    prob.run_model()

    site_spec_keys = ["tz", "elev", "lat", "lon"]
    time_keys = ["year", "month", "day", "hour", "minute"]
    resource_keys = ["dn", "df", "gh", "wspd", "tdry", "pres", "tdew"]
    with subtests.test("site timezone"):
        assert prob.get_val("solar.tz") == -6
    with subtests.test("data in local timezone"):
        assert prob.get_val("solar.solar_data_tz") == prob.get_val("solar.tz")
    for t in time_keys:
        with subtests.test(f"length of time profile: {t}"):
            assert len(prob.get_val(f"solar.{t}")) == 8760
    for t in resource_keys:
        with subtests.test(f"length of resource data profile: {t}"):
            assert len(prob.get_val(f"solar.{t}")) == 8760
    for t in site_spec_keys:
        with subtests.test(f"length of site info: {t}"):
            assert len(prob.get_val(f"solar.{t}")) == 1


# def test_solar_resouce_from_dict(subtests):
#     pass
