from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypedDict

from django_modern_rest.internal.json import Deserialize, Serialize

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.openapi.config import OpenAPIConfig


class DMRSettings(TypedDict, total=False):
    """TypedDict defining the shape of our settings."""

    serialize: str | Serialize
    deserialize: str | Deserialize
    openapi_config: 'OpenAPIConfig'
    validate_responses: bool
    responses: list[Any]
    global_error_handler: (
        str | Callable[['Blueprint[Any]', 'Endpoint', Exception], Any]
    )
