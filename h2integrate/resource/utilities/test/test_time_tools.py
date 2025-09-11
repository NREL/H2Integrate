from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

from h2integrate.resource.utilities.time_tools import (
    make_time_profile,
    roll_timeseries_data,
    convert_time_list_to_dict,
)


def test_make_time_profile_utc(subtests):
    dt = 3600
    n_timesteps = 10
    time_zone = 0
    start_time = "01/01/1999 00:30:00"
    time_profile = make_time_profile(start_time, dt, n_timesteps, time_zone)
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
    time_zone = 4
    start_time = "01/01/1999 00:30:00"
    replacement_year = 2024
    time_profile = make_time_profile(
        start_time, dt, n_timesteps, time_zone, start_year=replacement_year
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
        assert profile_tz == f"UTC+{time_zone:02d}:00"


def test_make_time_profile_start_year(subtests):
    dt = 600
    n_timesteps = 12
    time_zone = -4
    start_time = "01/01 00:30:00"
    replacement_year = 2024
    time_profile = make_time_profile(
        start_time, dt, n_timesteps, time_zone, start_year=replacement_year
    )
    t0 = time_profile[0].strftime("%m/%d/%Y %H:%M:%S (%z)")
    profile_dt = time_profile[1] - time_profile[0]
    with subtests.test("time profile length"):
        assert len(time_profile) == n_timesteps
    with subtests.test("time profile start time"):
        assert t0 == f"01/01/{replacement_year} 00:30:00 (-0400)"
    with subtests.test("time profile dt"):
        assert int(profile_dt.seconds) == dt


def test_roll_timeseries_data_same_starttime(subtests):
    dt = 3600
    n_timesteps = 8760

    local_time_zone = -5
    tz_utc_offset = timedelta(hours=local_time_zone)
    local_tz = timezone(offset=tz_utc_offset)
    local_time_now = datetime.now(tz=local_tz)
    utc_time_now = datetime.utcnow()

    # start time should be equivalent if either time is converted to the other timezone
    local_start_time = local_time_now.strftime("%m/%d/%Y %H:00:00")
    utc_start_time = utc_time_now.strftime("%m/%d/%Y %H:00:00")

    time_profile_local = make_time_profile(local_start_time, dt, n_timesteps, local_time_zone)
    time_profile_utc = make_time_profile(utc_start_time, dt, n_timesteps, 0)
    data_init = {
        "data": np.cumsum(np.ones(n_timesteps)),
        "time": time_profile_local,
        "id": 5.0,
    }

    # convert data from local to utc, rolling forward (utc is in the future)
    rolled_data = roll_timeseries_data(time_profile_utc, time_profile_local, data_init, dt)

    rolled_t0 = rolled_data["time"][0].astimezone(tz=time_profile_utc[0].tzinfo)
    rolled_t0_str = rolled_t0.strftime("%m/%d/%Y %H:%M:%S (%z)")
    desired_t0_str = time_profile_utc[0].strftime("%m/%d/%Y %H:%M:%S (%z)")
    with subtests.test("start time matches"):
        assert rolled_t0 == time_profile_utc[0]
    with subtests.test("start time strings match"):
        assert rolled_t0_str == desired_t0_str
    with subtests.test("start data is unchanged"):
        assert rolled_data["data"][0] == data_init["data"][0]
    with subtests.test("handled non-iterable"):
        assert "id" in rolled_data


def test_roll_timeseries_data_forward(subtests):
    dt = 3600
    n_timesteps = 8760

    local_time_zone = -5
    tz_utc_offset = timedelta(hours=local_time_zone)
    local_tz = timezone(offset=tz_utc_offset)
    local_time_now = datetime.now(tz=local_tz)

    hours_future = 2
    start_hour_offset = timedelta(hours=hours_future)

    # start time should be equivalent if either time is converted to the other timezone
    local_start_time = local_time_now.strftime("%m/%d/%Y %H:%M:%S")
    future_start_time = local_time_now + start_hour_offset

    time_profile_local = make_time_profile(local_start_time, dt, n_timesteps, local_time_zone)
    time_profile_future = make_time_profile(
        future_start_time.strftime("%m/%d/%Y %H:%M:%S"), dt, n_timesteps, local_time_zone
    )
    data_init = {
        "data": np.cumsum(np.ones(n_timesteps)),
        "time": time_profile_local,
        "id": 5.0,
    }

    # roll date forward (from time_local to time_future)
    rolled_data = roll_timeseries_data(time_profile_future, time_profile_local, data_init, dt)

    rolled_t0 = rolled_data["time"][0]
    rolled_t0_str = rolled_t0.strftime("%m/%d/%Y %H:%M:%S (%z)")
    desired_t0_str = time_profile_future[0].strftime("%m/%d/%Y %H:%M:%S (%z)")
    with subtests.test("start time matches"):
        assert rolled_t0 == time_profile_future[0]
    with subtests.test("start time strings match"):
        assert rolled_t0_str == desired_t0_str
    with subtests.test("start data is shifted"):
        assert rolled_data["data"][0] == data_init["data"][hours_future]
    with subtests.test("handled non-iterable"):
        assert "id" in rolled_data

    # roll date backwards (from time_future to time_local)
    rolled_data_reverse = roll_timeseries_data(
        time_profile_local, time_profile_future, rolled_data, dt
    )
    rolled_rev_t0 = rolled_data_reverse["time"][0]
    rolled_rev_t0_str = rolled_rev_t0.strftime("%m/%d/%Y %H:%M:%S (%z)")
    desired_rev_t0_str = time_profile_local[0].strftime("%m/%d/%Y %H:%M:%S (%z)")
    with subtests.test("reverse roll: start time matches"):
        assert rolled_rev_t0 == time_profile_local[0]
    with subtests.test("reverse roll: start time strings match"):
        assert rolled_rev_t0_str == desired_rev_t0_str
    with subtests.test("reverse roll: start data is shifted"):
        assert rolled_data_reverse["data"][0] == data_init["data"][0]


def test_convert_time_list_to_dict(subtests):
    dt = 3600
    n_timesteps = 8760
    tz_init = -4
    start_time = "01/01/2023 00:30:00"
    time_profile_datetime = make_time_profile(start_time, dt, n_timesteps, tz_init)
    time_str = [
        time_profile_datetime[i].strftime("%m/%d/%Y %H:%M:%S (%z)")
        for i in range(len(time_profile_datetime))
    ]
    time_dict = convert_time_list_to_dict(time_str)

    with subtests.test("timezone is the same"):
        assert time_dict["tz"] == "-0400"

    time_dict.pop("tz")
    input_time_profile = pd.to_datetime(time_profile_datetime)
    resulting_time_profile = pd.to_datetime(pd.DataFrame(time_dict))

    indices_to_check = [0, -1, 3760]
    for i in indices_to_check:
        with subtests.test(f"timezone as index {i} matches"):
            assert resulting_time_profile.iloc[i].strftime(
                "%m/%d/%Y %H:%M:%S"
            ) == input_time_profile[i].strftime("%m/%d/%Y %H:%M:%S")
