import operator
from functools import reduce

import pandas as pd


def getFromDict(dataDict, mapList):
    """Get value from nested dictionary using a list of keys.

    Allows for programmatic calling of items in a nested dict using a variable-length list.
    Instead of dataDict[item1][item2][item3][item4][item5], you can use
    getFromDict(dataDict, [item1, item2, item3, item4, item5]).

    Args:
        dataDict (dict): The nested dictionary to access.
        mapList (list): List of keys to traverse the nested dictionary.

    Returns:
        The value at the specified nested location in the dictionary.

    Example:
        >>> data = {"a": {"b": {"c": 42}}}
        >>> getFromDict(data, ["a", "b", "c"])
        42
    """
    return reduce(operator.getitem, mapList, dataDict)


def setInDict(dataDict, mapList, value):
    """Set value in nested dictionary using a list of keys.

    Allows for programmatic setting of items in a nested dict using a variable-length list.
    Instead of dataDict[item1][item2][item3][item4][item5] = value, you can use
    setInDict(dataDict, [item1, item2, item3, item4, item5], value).

    Args:
        dataDict (dict): The nested dictionary to modify.
        mapList (list): List of keys to traverse the nested dictionary.
        value: The value to set at the specified nested location.

    Example:
        >>> data = {"a": {"b": {}}}
        >>> setInDict(data, ["a", "b", "c"], 42)
        >>> data["a"]["b"]["c"]
        42
    """
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value


def load_tech_config_cases(case_file):
    """Load extensive lists of values from a spreadsheet to run many different cases.

    Loads tech_config values from a CSV file to run multiple cases with different
    technology configuration values.

    Args:
        case_file (Path): Path to the .csv file where the different tech_config values
            are listed. The CSV must be formatted with "Index 1", "Index 2", etc.
            columns followed by case name columns. Each row should have "technologies"
            as the first index value, followed by tech_name and parameter names.

    Returns:
        pd.DataFrame: DataFrame with the indexes of the tech_config as a MultiIndex
            and the different case names as the column names.

    Note:
        The CSV format should be:
        | "Index 1" | "Index 2" |...| "Index <N>" | <Case 1 Name> |...| <Case N Name> |
        | "technologies" | <tech_name> |...| <param_1_name> | <Case 1 value> |...| <Case N value> |
        | "technologies" | <tech_name> |...| <param_2_name> | <Case 1 value> |...| <Case N value> |
    """
    tech_config_cases = pd.read_csv(case_file)
    column_names = tech_config_cases.columns.values
    index_names = list(filter(lambda x: "Index" in x, column_names))
    tech_config_cases = tech_config_cases.set_index(index_names)

    return tech_config_cases


def modify_tech_config(h2i_model, tech_config_case):
    """Modify particular tech_config values on an existing H2I model before it is run.

    Args:
        h2i_model: H2IntegrateModel that has been set up but not run.
        tech_config_case (pd.Series): Series that was indexed from tech_config_cases
            DataFrame containing the parameter values to modify.

    Returns:
        H2IntegrateModel: The H2IntegrateModel with modified tech_config values.
    """
    for index_list, value in tech_config_case.items():
        setInDict(h2i_model.technology_config, index_list, float(value))

    return h2i_model
