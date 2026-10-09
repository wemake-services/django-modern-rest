import types
from contextlib import suppress
from typing import Any, Literal, Union, get_args, get_origin

from typing_extensions import TypeForm, get_type_hints

from dmr.openapi.objects import Encoding, Schema


def content_types(model: TypeForm[Any], property_name: str) -> str | None:
    """
    Get content types string from a model definition.

    We mostly use this for :data:`dmr.components.FileMetadata` component.
    We extract metadata from models like:

    .. code:: python

        >>> from typing import Literal
        >>> from pydantic import BaseModel

        >>> class ImageFile(BaseModel):
        ...     content_type: Literal['image/jpeg', 'image/png']

        >>> class LicenseFile(BaseModel):
        ...     content_type: str

        >>> class Payload(BaseModel):
        ...     avatar: ImageFile
        ...     license: LicenseFile
        ...     username: str

        >>> content_types(Payload, 'avatar')
        'image/jpeg, image/png'

        >>> assert content_types(Payload, 'license') is None
        >>> assert content_types(Payload, 'username') is None

    """
    with suppress(Exception):
        metadata = get_type_hints(model)[property_name]
        hints = get_type_hints(metadata)
        # We can't extract content types from anything other than `Literal`:
        if get_origin(hints['content_type']) is Literal:  # type: ignore[comparison-overlap, unused-ignore]
            return ', '.join(hints['content_type'].__args__)  # type: ignore[unreachable,  unused-ignore]
    return None


def encoding_for_files(
    model: Any,
    schema: Schema,
) -> dict[str, Encoding] | None:
    """Build multipart encoding, including optional and union file models."""
    encoding = {
        property_name: Encoding(content_type=content_type)
        for property_name in _property_names(schema)
        if (content_type := _merged_content_types(model, property_name))
        is not None
    }
    return encoding or None


def _property_names(schema: Schema) -> list[str]:
    names = list(schema.properties or ())
    for members in (schema.any_of, schema.one_of):
        names.extend(_member_names(members))
    return list(dict.fromkeys(names))


def _member_names(members: list[Schema] | None) -> list[str]:
    if not members:
        return []
    names: list[str] = []
    for member in members:
        names.extend(member.properties or ())
    return names


def _merged_content_types(model: Any, property_name: str) -> str | None:
    parts: list[str] = []
    for candidate in _file_models(model):
        content_type = content_types(candidate, property_name)
        if content_type is None:
            continue
        parts.extend(content_type.split(', '))
    unique = list(dict.fromkeys(parts))
    return ', '.join(unique) or None


def _file_models(model: Any) -> tuple[Any, ...]:
    if get_origin(model) not in {Union, types.UnionType}:
        return (model,)
    members = tuple(
        member for member in get_args(model) if member is not types.NoneType
    )
    return members or (model,)
