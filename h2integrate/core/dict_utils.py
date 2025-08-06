def update_defaults(orig_dict, keyname, new_val):
    """Recursive method

    Args:
        orig_dict (dict): _description_
        keyname (str): _description_
        new_val (any): _description_

    Returns:
        _type_: _description_
    """
    for key, val in orig_dict.items():
        if isinstance(val, dict):
            tmp = update_defaults(orig_dict.get(key, {}), keyname, new_val)
            orig_dict[key] = tmp
        else:
            if isinstance(key, list):
                for i, k in enumerate(key):
                    if k == keyname:
                        orig_dict[k] = new_val
                    else:
                        orig_dict[k] = orig_dict.get(key, []) + val[i]
            elif isinstance(key, str):
                if key == keyname:
                    orig_dict[key] = new_val
    return orig_dict


def update_keyname(orig_dict, init_key, new_keyname):
    """Recursive method

    Args:
        orig_dict (dict): _description_
        init_key (str): _description_
        new_keyname (str): _description_

    Returns:
        _type_: _description_
    """

    for key, val in orig_dict.copy().items():
        if isinstance(val, dict):
            tmp = update_keyname(orig_dict.get(key, {}), init_key, new_keyname)
            orig_dict[key] = tmp
        else:
            if isinstance(key, list):
                for i, k in enumerate(key):
                    if k == init_key:
                        orig_dict.update({new_keyname: orig_dict.get(k)})
                    else:
                        orig_dict[k] = orig_dict.get(key, []) + val[i]
            elif isinstance(key, str):
                if key == init_key:
                    orig_dict.update({new_keyname: orig_dict.get(key)})
    return orig_dict


def remove_keynames(orig_dict, init_key):
    """Recursive method

    Args:
        orig_dict (dict): _description_
        init_key (str): _description_

    Returns:
        dict: _description_
    """

    for key, val in orig_dict.copy().items():
        if isinstance(val, dict):
            tmp = remove_keynames(orig_dict.get(key, {}), init_key)
            orig_dict[key] = tmp
        else:
            if isinstance(key, list):
                for i, k in enumerate(key):
                    if k == init_key:
                        orig_dict.pop(k)
                    else:
                        orig_dict[k] = orig_dict.get(key, []) + val[i]
            elif isinstance(key, str):
                if key == init_key:
                    orig_dict.pop(key)
    return orig_dict


def rename_dict_keys(input_dict, init_keyname, new_keyname):
    """_summary_

    Args:
        input_dict (dict): _description_
        init_keyname (str): _description_
        new_keyname (str): _description_

    Returns:
        dict: _description_
    """
    input_dict = update_keyname(input_dict, init_keyname, new_keyname)
    input_dict = remove_keynames(input_dict, init_keyname)
    return input_dict
