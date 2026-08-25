import dataclasses
from typing import (
    Any,
    ClassVar,
    Final,
    Generic,
    TypeVar,
    final,
)

import pydantic
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.utils.http import parse_header_parameters
from typing_extensions import override

from dmr.files import FileBody, FileBodyLike
from dmr.metadata import EndpointMetadata
from dmr.openapi import OpenAPIContext
from dmr.openapi.objects import OpenAPIFormat, OpenAPIType, Reference, Schema
from dmr.parsers import DeserializeFunc, Parser, Raw, SupportsFileParsing
from dmr.serializer import BaseSerializer

OCTET_STREAM: Final = 'application/octet-stream'


@final
@dataclasses.dataclass(slots=True, frozen=True)
class _ByteStreamFileBody(FileBody):
    @override
    @classmethod
    def get_schema(
        cls,
        schema: Reference | Schema,
        context: OpenAPIContext,
    ) -> Schema:
        return Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.BINARY,
        )

    @override
    @classmethod
    def replace_schema(
        cls,
        schema: Reference | Schema,
        context: OpenAPIContext,
    ) -> Schema:
        return cls.get_schema(schema, context)


@final
class OctetStreamParser(SupportsFileParsing, Parser):
    """
    Parses ``application/octet-stream`` raw file uploads.

    Populates ``request.FILES`` with a ``SimpleUploadedFile`` created
    from the raw request body. Sets a parsed file as ``uploaded_file``.

    This class is private, because we don't want to encourage people
    to use Django to handle file upload. However, one can copy this file
    into their codebase and use it, if needed.
    """

    __slots__ = ()

    content_type = 'application/octet-stream'
    default_field_name: ClassVar[str] = 'uploaded_file'
    default_filename: ClassVar[str] = 'file'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> None:
        """Populate ``request.FILES`` from raw request body."""
        content_disposition = request.headers.get('Content-Disposition')
        if content_disposition:
            _, disposition_params = parse_header_parameters(content_disposition)
        else:
            disposition_params = {}

        field_name = disposition_params.get('name') or self.default_field_name
        filename = disposition_params.get('filename') or self.default_filename

        # It does not support multiple files by design,
        # because it is designed to be a single-file upload feature:
        request.FILES[field_name] = SimpleUploadedFile(
            filename,
            request.body,
            content_type=self.content_type,
        )

    @override
    def schema_metadata(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> type['FileBodyLike']:
        """Provide schema for the file request spec."""
        return _ByteStreamFileBody


_ModelT = TypeVar('_ModelT')


@final
class OctetFileModel(pydantic.BaseModel, Generic[_ModelT]):
    """File metadata model for OctetParser."""

    uploaded_file: _ModelT

    @classmethod
    @override
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:  # noqa: WPS110
        return (
            super()
            .model_parametrized_name(params)
            .replace('[', '_')
            .replace(']', '_')
        )
