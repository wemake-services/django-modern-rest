import abc
from collections.abc import Callable
from typing import ClassVar, TypeAlias

from django.http import HttpRequest, HttpResponse

from django_modern_rest.openapi.converter import ConvertedSchema

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
    return serialize(schema, None).decode('utf-8')  # type: ignore[no-any-return]


class BaseRenderer:
    """
    Abstract base class for OpenAPI schema renderers.

    Provides common interface for rendering OpenAPI schemas into different
    formats (JSON, HTML, etc.). Subclasses must implement the render method
    and define default configuration values.

    Attributes:
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
        path: str | None = None,
        name: str | None = None,
    ) -> None:
        """
        Initialize renderer with optional custom path and name.

        Args:
            path: Custom URL path, uses `default_path` if not provided.
            name: Custom name identifier, uses `default_name` if not provided.
        """
        self.path = self.default_path if path is None else path
        self.name = self.default_name if name is None else name

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
