from typing import Any

from django.utils.datastructures import MultiValueDict


def convert_multi_value_dict(
    to_parse: 'MultiValueDict[str, Any]',
    force_list: frozenset[str],
) -> dict[str, Any]:
    """
    Convert multi value dictionary to a regular one.

    Utility function to parse django's
    :class:`django.utils.datastructures.MultiValueDict`
    into a regular :class:`dict`. To do that, we require explicit *force_list*
    parameter to return lists as dict values. Otherwise, single value is set.

    We use the last value that is sent via query,
    if there are multiple ones and only one is needed.
    """
    regular_dict: dict[str, Any] = {}
    for dict_key in to_parse:
        if dict_key in force_list:
            regular_dict[dict_key] = to_parse.getlist(dict_key)
        else:
            regular_dict[dict_key] = to_parse[dict_key]
    return regular_dict
