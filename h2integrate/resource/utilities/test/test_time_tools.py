import numpy as np

from h2integrate.resource.utilities.time_tools import make_time_profile, roll_timeseries_data


def test_make_time_profile_utc(subtests):
    dt = 3600
    n_timesteps = 10
    timezone = 0
    start_time = "01/01/1999 00:30:00"
    time_profile = make_time_profile(start_time, dt, n_timesteps, timezone)
    t0 = time_profile[0].strftime("%m/%d/%Y %H:%M:%S (%z)")
    profile_dt = time_profile[1] - time_profile[0]
    profile_tz = str(time_profile[0].tzinfo)
    with subtests.test("time profile length"):
        assert len(time_profile) == n_timesteps
    with subtests.test("time profile start time"):
        assert t0 == "01/01/1999 00:30:00 (+0000)"
    with subtests.test("time profile dt"):
        assert int(profile_dt.seconds) == dt
    with subtests.test("time profile timezone"):
        assert profile_tz == "UTC"


def test_make_time_profile_replace_start_year(subtests):
    dt = 3600
    n_timesteps = 10
    timezone = 4
    start_time = "01/01/1999 00:30:00"
    replacement_year = 2024
    time_profile = make_time_profile(
        start_time, dt, n_timesteps, timezone, start_year=replacement_year
    )
    t0 = time_profile[0].strftime("%m/%d/%Y %H:%M:%S (%z)")
    profile_dt = time_profile[1] - time_profile[0]
    profile_tz = str(time_profile[0].tzinfo)
    with subtests.test("time profile length"):
        assert len(time_profile) == n_timesteps
    with subtests.test("time profile start time"):
        assert t0 == f"{start_time.replace('1999',str(replacement_year))} (+0400)"
    with subtests.test("time profile dt"):
        assert int(profile_dt.seconds) == dt
    with subtests.test("time profile timezone"):
        assert profile_tz == f"UTC+{timezone:02d}:00"


def test_make_time_profile_start_year(subtests):
    dt = 600
    n_timesteps = 12
    timezone = -4
    start_time = "01/01 00:30:00"
    replacement_year = 2024
    time_profile = make_time_profile(
        start_time, dt, n_timesteps, timezone, start_year=replacement_year
    )
    t0 = time_profile[0].strftime("%m/%d/%Y %H:%M:%S (%z)")
    profile_dt = time_profile[1] - time_profile[0]
    with subtests.test("time profile length"):
        assert len(time_profile) == n_timesteps
    with subtests.test("time profile start time"):
        assert t0 == f"01/01/{replacement_year} 00:30:00 (-0400)"
    with subtests.test("time profile dt"):
        assert int(profile_dt.seconds) == dt


def test_roll_timeseries_data():
    dt = 3600
    n_timesteps = 12
    tz_init = -4
    tz_desired = 0
    start_time = "01/01/2024 00:30:00"
    time_profile_init = make_time_profile(start_time, dt, n_timesteps, tz_init)
    time_profile_desired = make_time_profile(start_time, dt, n_timesteps, tz_desired)
    data_init = {
        "data": np.cumsum(np.ones(n_timesteps)),
        "time": time_profile_init,
    }
    rolled_data = roll_timeseries_data(time_profile_desired, time_profile_init, data_init, dt)
    assert rolled_data["time"][0] == time_profile_desired[0]
