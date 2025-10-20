import abc
from collections.abc import Callable
from typing import ClassVar, TypeAlias, cast, final

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from typing_extensions import override

from django_modern_rest.openapi.converter import ConvertedSchema
from django_modern_rest.types import Empty, EmptyObj

SerializedSchema: TypeAlias = str
SchemaSerialier: TypeAlias = Callable[[ConvertedSchema], SerializedSchema]


def json_serializer(schema: ConvertedSchema) -> SerializedSchema:
    """
    Serialize `ConvertedSchema` to decoded JSON string.

    Uses the configured serializer from `DMR` settings to convert
    the schema to JSON format.

    Args:
        schema: Converted OpenAPI schema to serialize.

    Returns:
        JSON string representation of the schema.
    """
    from django_modern_rest.settings import (  # noqa: PLC0415
        DMR_SERIALIZE_KEY,
        resolve_setting,
    )

    serialize = resolve_setting(DMR_SERIALIZE_KEY, import_string=True)
    return cast(SerializedSchema, serialize(schema, None).decode('utf-8'))


class BaseRenderer(abc.ABC):
    """
    Abstract base class for OpenAPI schema renderers.

    Provides common interface for rendering OpenAPI schemas into different
    formats (JSON, HTML, etc.). Subclasses must implement the render method
    and define default configuration values.

    Attrs:
        default_path: Default URL path for the renderer endpoint.
        default_name: Default name identifier for the renderer.
        content_type: MIME type of the rendered content.
        serializer: Function to convert schema to serialized format.
    """

    __slots__ = (
        'content_type',
        'name',
        'path',
        'serializer',
    )

    default_path: ClassVar[str]
    default_name: ClassVar[str]
    content_type: ClassVar[str]
    serializer: SchemaSerialier

    def __init__(
        self,
        *,
        path: str | Empty = EmptyObj,
        name: str | Empty = EmptyObj,
    ) -> None:
        """
        Initialize renderer with optional custom path and name.

        Args:
            path: Custom URL path, uses `default_path` if not provided.
            name: Custom name identifier, uses `default_name` if not provided.
        """
        self.path = self.default_path if isinstance(path, Empty) else path
        self.name = self.default_name if isinstance(name, Empty) else name

    @abc.abstractmethod
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """
        Render OpenAPI schema into HTTP response.

        Args:
            request: Django HTTP request object.
            schema: Converted OpenAPI schema to render.

        Returns:
            Django HTTP response with rendered content.
        """
        raise NotImplementedError


@final
class JsonRenderer(BaseRenderer):
    """
    Renderer for OpenAPI schema in JSON format.

    Provides JSON representation of OpenAPI specification suitable for
    API documentation tools and client code generation.
    """

    default_path: ClassVar[str] = 'openapi.json/'
    default_name: ClassVar[str] = 'json'
    content_type: ClassVar[str] = 'application/json'
    serializer: SchemaSerialier = staticmethod(json_serializer)  # noqa: WPS421

    @override
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """Render the OpenAPI schema as JSON response."""
        return HttpResponse(
            content=self.serializer(schema),
            content_type=self.content_type,
        )


@final
class SwaggerRenderer(BaseRenderer):
    """
    Renderer for OpenAPI schema using Swagger UI.

    Provides interactive HTML interface for exploring OpenAPI specification
    using Swagger UI components.
    """

    default_path: ClassVar[str] = 'swagger/'
    default_name: ClassVar[str] = 'swagger'
    content_type: ClassVar[str] = 'text/html'
    template_name: ClassVar[str] = 'django_modern_rest/swagger.html'
    serializer: SchemaSerialier = staticmethod(json_serializer)  # noqa: WPS421

    @override
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """Render the OpenAPI schema using Swagger UI template."""
        return render(
            request,
            self.template_name,
            context={'schema': self.serializer(schema)},
            content_type=self.content_type,
        )
