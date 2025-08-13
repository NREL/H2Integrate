import json
import time
from pathlib import Path

import pandas as pd
import requests


def get_tz_info_from_solar_resource_file(filepath):
    header_info = pd.read_csv(filepath, nrows=1)
    local_tz = header_info["Local Time Zone"].iloc[0]
    data_tz = header_info["Time Zone"].iloc[0]
    return {"data_tz": data_tz, "local_tz": local_tz}


def download_from_api(url, filename):
    """
    Args:
        url (str): The API endpoint to return data from
        filename (str): The filename where data should be written

    Returns:
        True if downloaded file successfully, False if encountered error in downloading

    """
    n_tries = 0
    success = False
    while n_tries < 5:
        try:
            r = requests.get(url)
            if r:
                localfile = Path(filename).open("w+")
                txt = r.text.replace("(Â°C)", "(C)").replace("(Â°)", "(deg)")
                localfile.write(txt)
                localfile.close()
                if Path(filename).is_file():
                    success = True
                    break
            elif r.status_code == 400 or r.status_code == 403:
                print(r.url)
                err = r.text
                text_json = json.loads(r.text)
                if "errors" in text_json.keys():
                    err = text_json["errors"]
                raise requests.exceptions.HTTPError(err)
            elif r.status_code == 404:
                print(filename)
                raise requests.exceptions.HTTPError
            elif r.status_code == 429:
                raise RuntimeError("Maximum API request rate exceeded!")
            else:
                n_tries += 1
        except requests.exceptions.Timeout:
            time.sleep(0.2)
            n_tries += 1

    return success
