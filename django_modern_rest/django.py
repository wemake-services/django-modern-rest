from collections.abc import Mapping
from typing import Any, Final, TypeAlias

from django.core.files.uploadedfile import UploadedFile
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


_FileMetadata: TypeAlias = dict[str, Any]


def exctract_files_metadata(
    request_files: MultiValueDict[str, UploadedFile],
    force_list: frozenset[str],
) -> Mapping[str, _FileMetadata | list[_FileMetadata]]:
    """Extracts file metadata from ``request.FILES`` from Django."""
    metadata: dict[str, _FileMetadata | list[_FileMetadata]] = {}
    for key_name in request_files:
        if key_name in force_list:
            metadata[key_name] = _process_files_metadata(
                request_files.getlist(key_name),
            )
        else:
            metadata[key_name] = _process_files_metadata(
                request_files[key_name],  # type: ignore[arg-type]
            )
    return metadata


_FILE_ATTRS: Final = (
    'size',
    'name',
    'content_type',
    'charset',
    'content_type_extra',
)


def _process_files_metadata(
    uploaded: UploadedFile | list[UploadedFile],
) -> _FileMetadata | list[_FileMetadata]:
    if isinstance(uploaded, UploadedFile):
        return _process_file_metadata(uploaded)

    return [_process_file_metadata(single_file) for single_file in uploaded]


def _process_file_metadata(uploaded: UploadedFile) -> _FileMetadata:
    return {
        attr_name: getattr(uploaded, attr_name, None)
        for attr_name in _FILE_ATTRS
    }
