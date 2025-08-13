from rex import NSRDBX
from rex.sam_resource import SAMResource


def pull_solar_resource(dataset_fpath, lat, lon, interval, use_utc):
    with NSRDBX(dataset_fpath, hsds=False) as f:
        site_gid = f.lat_lon_gid((lat, lon))

        # extract timezone, elevation, latitude and longitude from meta dataset with gid
        tz = f.meta["timezone"].iloc[site_gid]
        elev = f.meta["elevation"].iloc[site_gid]
        nsrdb_latitude = f.meta["latitude"].iloc[site_gid]
        nsrdb_longitude = f.meta["longitude"].iloc[site_gid]
        year_arr = f.time_index.year.values
        month_arr = f.time_index.month.values
        day_arr = f.time_index.day.values
        hour_arr = f.time_index.hour.values
        minute_arr = f.time_index.minute.values
        dni_arr = f["dni", :, site_gid]
        dhi_arr = f["dhi", :, site_gid]
        ghi_arr = f["ghi", :, site_gid]
        wspd_arr = f["wind_speed", :, site_gid]
        tdry_arr = f["air_temperature", :, site_gid]
        pres_arr = f["surface_pressure", :, site_gid]
        tdew_arr = f["dew_point", :, site_gid]

    data = {
        "site_gid": site_gid,
        "site_lat": nsrdb_latitude,
        "site_lon": nsrdb_longitude,
        "tz": tz,
        "elev": elev,
        "lat": nsrdb_latitude,
        "lon": nsrdb_longitude,
        "year": year_arr,
        "month": month_arr,
        "day": day_arr,
        "hour": hour_arr,
        "minute": minute_arr,
        "dn": dni_arr,
        "df": dhi_arr,
        "gh": ghi_arr,
        "wspd": wspd_arr,
        "tdry": tdry_arr,
        "pres": pres_arr,
        "tdew": tdew_arr,
    }
    if interval == 60:
        for key, val in data.items():
            if not isinstance(val, (str, float, int)):
                new_val = val[1::2]
                data.update({key: new_val})
    if use_utc:
        return data

    # convert to local timezone
    for key, val in data.items():
        data[key] = SAMResource.roll_timeseries(val, tz, int(60 / interval))
    return data
