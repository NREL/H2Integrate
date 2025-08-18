def update_defaults(orig_dict, keyname, new_val):
    """Recursive method to update all entries in a dictionary with key 'keyname'
    with value 'new_val'

    Args:
        orig_dict (dict): dictionary to update
        keyname (str): key corresponding to value to update
        new_val (any): value to use for ``keyname``

    Returns:
        dict: updated version of orig_dict
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
    """Recursive method to copy value of ``orig_dict[init_key]`` to ``orig_dict[new_keyname]``

    Args:
        orig_dict (dict): dictionary to update.
        init_key (str): existing key
        new_keyname (str): new key to replace ``init_key``

    Returns:
        dict: updated dictionary
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
    """Recursive method to remove keys from a dictionary.

    Args:
        orig_dict (dict): input dictionary
        init_key (str): key name to remove from dictionary

    Returns:
        dict: dictionary without any keys named `init_key`
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
    """Rename ``input_dict[init_keyname]`` to ``input_dict[new_keyname]``

    Args:
        input_dict (dict): dictionary to update
        init_keyname (str): existing key to replace
        new_keyname (str): new keyname

    Returns:
        dict: updated dictionary
    """
    input_dict = update_keyname(input_dict, init_keyname, new_keyname)
    input_dict = remove_keynames(input_dict, init_keyname)
    return input_dict
