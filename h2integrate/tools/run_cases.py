import operator
from functools import reduce

import numpy as np
import pandas as pd


"""
getFromDict()
setFromDict()

Allows for programmatic calling of items in a nested dict using a variable-length list
E.g. instead of
    dataDict[item1][item2][item3][item4][item5] = value
or
    dataDict[item1][item2][item3][item4][item5]
We can just say
    getFromDict(dataDict, mapList)
or
    setFromDict(dataDict, mapList, value)
To achieve the same results, where
    mapList = [item1,item2,item3,item4,item5]
"""


def getFromDict(dataDict, mapList):
    return reduce(operator.getitem, mapList, dataDict)


def setInDict(dataDict, mapList, value):
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value


"""
load_tech_config_cases()

Loads extensive lists of values from a spreadsheet to run many different cases with different
tech_config values.

Input: case_file (Path) - Path to the .csv file where the different tech_config values are listed.
    This .csv must be formatted like so:
           "Index 1"   |  "Index 2"  | ... |  "Index <N>"   | <Case 1 Name>  | ... | <Case N Name>|
        "technologies" | <tech_name> | ... | <param_1_name> | <Case 1 value> | ... |<Case N value>|
        "technologies" | <tech_name> | ... | <param_2_name> | <Case 1 value> | ... |<Case N value>|
        .                                                                                         .
        .                                                                                         .
        .                                                                                         .
        "technologies" | <tech_name> | ... | <param_N_name> | <Case 1 value> | ... |<Case N value>|

Output: tech_config_cases - DataFrame with the indexes of the tech_config as a MultiIndex and the
        different case names as the column names
"""


def load_tech_config_cases(case_file):
    tech_config_cases = pd.read_csv(case_file)
    column_names = tech_config_cases.columns.values
    index_names = list(filter(lambda x: "Index" in x, column_names))
    tech_config_cases = tech_config_cases.set_index(index_names)

    return tech_config_cases


"""
mod_tech_config()

Modifies particular tech_config values on an existing H2I model before it is run

Inputs: h2i_model: H2IntegrateModel that has been set up but not run
        tech_config_case: Series that was indexed from tech_config_cases DataFrame

Output: h2i_model: H2IntegrateModel that is modified with the new tech_config values

"""


def mod_tech_config(h2i_model, tech_config_case):
    for index_tup, value in tech_config_case.items():
        index_list = list(index_tup)
        while np.nan in index_list:
            index_list.remove(np.nan)
        setInDict(h2i_model.technology_config, index_list, float(value))

    return h2i_model
