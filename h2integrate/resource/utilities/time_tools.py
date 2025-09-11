from datetime import datetime, timezone, timedelta

import numpy as np


def make_time_profile(
    start_time: str,
    dt: float | int,
    n_timesteps: int,
    time_zone: int | float,
    start_year: int | None = None,
):
    """Generate a time-series profile for a given start time, time step interval, and
    number of timesteps, with a timezone signature.

    Args:
        start_time (str): simulation start time formatted as 'mm/dd/yyyy HH:MM:SS' or
            'mm/dd HH:MM:SS'
        dt (float | int): time step interval in seconds.
        n_timesteps (int): number of timesteps in a simulation.
        time_zone (int | float): timezone offset from UTC in hours.
        start_year (int | None, optional): year to use for start-time. if start-time
            is formatted as 'mm/dd/yyyy HH:MM:SS' then will overwrite original year.
            If None, the year will default to 1900 if start-time is formatted as 'mm/dd HH:MM:SS'.
            Defaults to None.

    Returns:
        list[datetime]: list of datetime objects that represents the time profile
    """

    tz_utc_offset = timedelta(hours=time_zone)
    tz = timezone(offset=tz_utc_offset)
    tz_str = str(tz).replace("UTC", "").replace(":", "")
    if tz_str == "":
        tz_str = "+0000"
    # timezone formatted as ±HHMM[SS[.ffffff]]
    start_time_w_tz = f"{start_time} ({tz_str})"
    if len(start_time.split("/")) == 3:
        if start_year is not None:
            start_time_month_day_year, start_time_time = start_time.split(" ")
            start_time_month_day = "/".join(i for i in start_time_month_day_year.split("/")[:-1])
            start_time_w_tz = f"{start_time_month_day}/{start_year} {start_time_time} ({tz_str})"

        t = datetime.strptime(start_time_w_tz, "%m/%d/%Y %H:%M:%S (%z)")
    elif len(start_time.split("/")) == 2:
        if start_year is not None:
            start_time_month_day, start_time_time = start_time.split(" ")
            start_time_w_tz = f"{start_time_month_day}/{start_year} {start_time_time} ({tz_str})"
            t = datetime.strptime(start_time_w_tz, "%m/%d/%Y %H:%M:%S (%z)")
        else:
            # NOTE: year will default to 1900
            t = datetime.strptime(start_time_w_tz, "%m/%d %H:%M:%S (%z)")
    time_profile = [None] * n_timesteps
    time_step = timedelta(seconds=dt)
    for i in range(n_timesteps):
        time_profile[i] = t
        t += time_step
    return time_profile


def roll_timeseries_data(desired_time_profile, data_time_profile, data, dt):
    """Roll timeseries data from its time profile (`data_time_profile`)
    to the `desired_time_profile`.

    Args:
        desired_time_profile (list[datetime.datetime]): time profile to roll data too.
        data_time_profile (list[datetime.datetime]: time profile that data is currently in.
        data (dict): dictionary of data to roll.
        dt (int): length of time step in seconds.

    Returns:
        dict: data rolled to `desired_time_profile`
    """
    # 1) align timezones
    t0_desired = desired_time_profile[0]
    t0_actual_in_desired_tz = data_time_profile[0].astimezone(tz=t0_desired.tzinfo)

    # 2) calculate time difference
    start_time_offset = t0_actual_in_desired_tz - t0_desired
    seconds_per_day = 24 * 3600

    # 3) calculate time different in units of dt
    start_time_offset_in_dt = (
        start_time_offset.seconds + seconds_per_day * start_time_offset.days
    ) / dt

    if np.abs(start_time_offset_in_dt) < 1:
        return data

    # NOTE: should check if roll amount is an integer or if its some partial step
    roll_by = int(start_time_offset_in_dt)
    rolled_data = {}
    for var, values in data.items():
        if isinstance(values, (str, float, int, bool)):
            rolled_data[var] = values
        if var != "time" and not isinstance(values, (str, float, int, bool)):
            vals_rolled = np.roll(values, roll_by)
            rolled_data[var] = vals_rolled
        if var == "time":
            time_index = list(range(len(values)))
            index_rolled = np.roll(time_index, roll_by)
            time_rolled = [values[i] for i in index_rolled]
            rolled_data[var] = time_rolled
    return rolled_data


def convert_time_list_to_dict(time_list_str):
    """Create a dictionary representing the time from a list of time-represented strings
    with keys of:

        - **Year** (*array*): Year with century (1999, 2000, ..., 2024).
        - **Month** (*array*): Month as zero-padded number (01, 02, ..., 12).
        - **Day** (*array*): Day of the month as a zero-padded number (01, 02, ..., 31).
        - **Hour** (*array*): Hour (24-hour clock) as a zero-padded number (00, 01, ..., 23).
        - **Minute** (*array*): Minute as a zero-padded number (00, 01, ..., 59).
        - **tz** (*float | int*): timezone of the time profile

    Args:
        time_list_str (list[str]): list of strings representing the time,
            formatted as "%m/%d/%Y %H:%M:%S (%z)".

    Returns:
        dict: dictionary of data representing the time profile.
    """
    years = np.array(len(time_list_str))
    months = np.array(len(time_list_str))
    days = np.array(len(time_list_str))
    hours = np.array(len(time_list_str))
    minutes = np.array(len(time_list_str))
    for i, time_str in enumerate(time_list_str):
        date = datetime.strptime(time_str, "%m/%d/%Y %H:%M:%S (%z)")
        years[i] = date.year
        months[i] = date.month
        days[i] = date.day
        hours[i] = date.hour
        minutes[i] = date.minute
    tz = str(date.tzinfo).replace("UTC", "").replace(":", "")
    if tz == "":
        tz = 0
    time_dict = {
        "Year": years,
        "Month": months,
        "Day": days,
        "Hour": hours,
        "Minute": minutes,
        "tz": float(tz),
    }
    return time_dict
