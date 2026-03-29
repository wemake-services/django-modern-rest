from contextlib import suppress
from typing import Any, Literal, get_origin

from typing_extensions import get_type_hints


def content_types(model: Any, property_name: str) -> str | None:
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
            return ', '.join(hints['content_type'].__args__)
    return None
