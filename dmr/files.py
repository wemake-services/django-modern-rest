import dataclasses
from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from typing_extensions import override

from dmr.headers import HeaderSpec
from dmr.metadata import EndpointMetadata, ResponseSpec
from dmr.openapi import OpenAPIContext
from dmr.openapi.mappers.content_types import content_types
from dmr.openapi.objects import (
    Encoding,
    MediaType,
    OpenAPIFormat,
    OpenAPIType,
    Reference,
    Response,
    Schema,
)

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(slots=True, frozen=True)
class FileBody:
    """Special type that indicates that response returns a file body."""

    @classmethod
    def media_type(
        cls,
        schema: Schema | Reference,
        model: Any,
        context: 'OpenAPIContext',
    ) -> MediaType:
        """Returns the media type for the given file."""
        schema = context.registries.schema.maybe_resolve_reference(schema)
        schema = dataclasses.replace(
            schema,
            properties={
                property_name: cls.get_schema()
                for property_name in (schema.properties or [])
            },
        )
        return MediaType(
            schema=schema,
            encoding=cls.encoding(model, schema),
        )

    @classmethod
    def get_schema(cls) -> Schema:
        """Returns the openapi schema that this object represents."""
        return Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.BINARY)

    @classmethod
    def encoding(
        cls,
        model: Any,
        schema: Schema,
    ) -> dict[str, Encoding] | None:
        """Returns the openapi encoding for the defined media type."""
        return {
            property_name: Encoding(content_type=content_type)
            for property_name in (schema.properties or [])
            if (content_type := content_types(model, property_name)) is not None
        } or None


@dataclasses.dataclass(frozen=True, slots=True)
class FileResponseSpec(ResponseSpec):
    """
    Special :class:`~dmr.metadata.ResponseSpec` subclass for files.

    Attributes:
        file_body: Model to be used for file body schema generation.

    """

    return_type: type[FileBody] = FileBody
    status_code: HTTPStatus = dataclasses.field(
        kw_only=True,
        default=HTTPStatus.OK,
    )
    headers: Mapping[str, HeaderSpec] | None = dataclasses.field(
        kw_only=True,
        default_factory=lambda: {
            'Content-Length': HeaderSpec(),
            'Content-Disposition': HeaderSpec(),
        },
    )
    file_body: type[FileBody] = dataclasses.field(
        kw_only=True,
        default=FileBody,
    )

    @override
    def get_schema(
        self,
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: OpenAPIContext,
    ) -> Response:
        """Customize schema for the file response."""
        response = ResponseSpec.get_schema(self, metadata, serializer, context)
        # We know that we return files:
        for media in (response.content or {}).values():
            media.schema = self.file_body.get_schema()
        # We know that `FileBody` was a fake model, remove it:
        context.registries.schema.try_unregister(
            serializer.schema_generator.schema_name(self.file_body),
        )
        return response
