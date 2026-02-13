import abc
from collections.abc import Callable
from typing import Any, ClassVar, TypeAlias

from django.http import HttpRequest, HttpResponse

from django_modern_rest.internal.json import (
    SerializedSchema as SerializedSchema,
)
from django_modern_rest.internal.json import json_dumps
from django_modern_rest.openapi.converter import ConvertedSchema

SchemaSerializer: TypeAlias = Callable[[ConvertedSchema], SerializedSchema]
_CallableAny: TypeAlias = Callable[..., Any]
_ViewDecorator: TypeAlias = Callable[[_CallableAny], _CallableAny]


def json_serializer(schema: ConvertedSchema) -> SerializedSchema:
    """
    Serialize ``ConvertedSchema`` to decoded JSON string.

    Uses the configured serializer from DMR settings to convert
    the schema to JSON format.

    Args:
        schema: Converted OpenAPI schema to be serialized.

    Returns:
        JSON string representation of the schema.

    """
    return json_dumps(schema)


class BaseRenderer:
    """
    Abstract base class for OpenAPI schema renderers.

    Provides common interface for rendering OpenAPI schemas into different
    formats (JSON, HTML, etc.). Subclasses must implement the render method
    and define default configuration values.

    Attributes:
        path: URL path for the renderer endpoint.
        name: Name identifier for the renderer.
        decorators: List of decorators to apply to the renderer.
        content_type: MIME type of the rendered content.
        serializer: Function to convert schema to serialized format.
    """

    __slots__ = (
        'content_type',
        'decorators',
        'name',
        'path',
        'serializer',
    )
    default_path: ClassVar[str]
    default_name: ClassVar[str]
    content_type: ClassVar[str]
    serializer: SchemaSerializer

    def __init__(
        self,
        *,
        path: str | None = None,
        name: str | None = None,
        decorators: list[_ViewDecorator] | None = None,
    ) -> None:
        """
        Initialize renderer with optional parameters.

        Args:
            path: Custom URL path, uses `default_path` if not provided.
            name: Custom name identifier, uses `default_name` if not provided.
            decorators: List of decorators to apply to the renderer.
        """
        self.path = self.default_path if path is None else path
        self.name = self.default_name if name is None else name
        self.decorators = decorators

    @abc.abstractmethod
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """
        Render OpenAPI schema into HTTP response.

        Args:
            request: Django `HttpRequest` object.
            schema: Converted OpenAPI schema to render.

        Returns:
            Django `HttpResponse` with rendered content.
        """
        raise NotImplementedError
