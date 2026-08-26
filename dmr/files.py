import abc
import dataclasses
from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from typing_extensions import override

from dmr.headers import HeaderSpec
from dmr.metadata import EndpointMetadata, ResponseSpec, get_annotated_metadata
from dmr.negotiation import get_conditional_types
from dmr.openapi import OpenAPIContext
from dmr.openapi.mappers.content_types import content_types
from dmr.openapi.objects import (
    Encoding,
    MediaType,
    MediaTypeMetadata,
    OpenAPIFormat,
    OpenAPIType,
    Reference,
    Response,
    Schema,
)
from dmr.parsers import Parser

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer


def file_response_headers(
    headers: Mapping[str, HeaderSpec] | None,
    *,
    as_attachment: bool,
) -> Mapping[str, HeaderSpec]:
    """Build headers expected from ``FileResponse``."""
    response_headers = {
        'Content-Length': HeaderSpec(),
        **(headers or {}),
    }
    if as_attachment:
        response_headers['Content-Disposition'] = HeaderSpec()
    return response_headers


class FileBodyLike:
    """
    Interface that describes objects that can return media type schema.

    .. versionadded:: 0.15.0
    """

    __slots__ = ()

    @classmethod
    @abc.abstractmethod
    def media_type(
        cls,
        schema: Reference | Schema,
        model: Any,
        model_meta: tuple[Any, ...],
        parser: Parser,
        context: 'OpenAPIContext',
    ) -> MediaType:
        """Provides file request schema for this parser."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_schema(
        cls,
        schema: Reference | Schema,
        context: 'OpenAPIContext',
    ) -> Schema:
        """Return the OpenAPI schema for this file body."""
        raise NotImplementedError


@dataclasses.dataclass(slots=True, frozen=True)
class FileBody(FileBodyLike):
    """Special type that indicates that response returns a file body."""

    @override
    @classmethod
    def media_type(
        cls,
        schema: Reference | Schema,
        model: Any,
        model_meta: tuple[Any, ...],
        parser: Parser,
        context: 'OpenAPIContext',
    ) -> MediaType:
        """Returns the media type for the given file."""
        schema = cls.replace_schema(schema, context)
        conditional_models = get_conditional_types(model, model_meta) or {}
        media_type_meta = (
            get_annotated_metadata(
                conditional_models.get(parser.content_type, model),
                MediaTypeMetadata,
                model_meta=model_meta,
            )
            or MediaTypeMetadata()
        )
        return MediaType(
            schema=schema,
            encoding=media_type_meta.encoding or cls._encoding(model, schema),
            example=media_type_meta.example,
            examples=media_type_meta.examples,
            item_encoding=media_type_meta.item_encoding,
            prefix_encoding=media_type_meta.prefix_encoding,
        )

    @override
    @classmethod
    def get_schema(
        cls,
        schema: Reference | Schema,
        context: 'OpenAPIContext',
    ) -> Schema:
        """Returns the openapi schema that this object represents."""
        file_schema = Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.BINARY,
        )
        if isinstance(schema, Schema) and schema.type == OpenAPIType.ARRAY:
            return Schema(
                type=OpenAPIType.ARRAY,
                format=schema.format,
                items=file_schema,
            )
        return file_schema

    @classmethod
    def replace_schema(
        cls,
        schema: Reference | Schema,
        context: 'OpenAPIContext',
    ) -> Schema:
        """
        Replaces existing generated schema with file-like schema.

        Here the most tricky part happens. When we define
        ``FileMetadata[Info]`` as a model to parse, we don't want
        to expose ``Info`` as a model actually, we want to show
        that this is a file in the OpenAPI schema. So, we place known models
        with the file specification here.

        .. versionadded:: 0.15.0
        """
        schema = context.registries.schema.maybe_resolve_reference(schema)
        return dataclasses.replace(
            schema,
            properties={
                property_name: cls.get_schema(second, context)
                for property_name, second in (schema.properties or {}).items()
            },
        )

    @classmethod
    def _encoding(
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

    Unlike regular ``ResponspeSpec`` that will create
    a real schema for the return type, here we force
    to use :class:`dmr.files.FileBodyLike` schema providers,
    that know how files will look like in the final schema.

    Attributes:
        as_attachment: Marks responses with ``Content-Disposition`` header
            as required. Use together with ``FileResponse(as_attachment=True)``.

    .. versionchanged:: 0.10.0
        Added ``as_attachment`` parameter that can mark files
        that should be sent via ``Content-Disposition`` header.
        Similar to Django's ``as_attachment`` parameter
        in :class:`django.http.FileResponse`.

    .. versionchanged:: 0.15.0
        Removed ``file_body`` attribute, now using ``return_type`` instead
        to generate the response schema.

    """

    return_type: type[FileBodyLike] = FileBody
    status_code: HTTPStatus = dataclasses.field(
        kw_only=True,
        default=HTTPStatus.OK,
    )
    headers: Mapping[str, HeaderSpec] | None = dataclasses.field(
        kw_only=True,
        default=None,
    )
    as_attachment: bool = dataclasses.field(kw_only=True, default=False)

    @override
    def __post_init__(self) -> None:
        """Set required headers depending on how files are returned."""
        ResponseSpec.__post_init__(self)
        object.__setattr__(
            self,
            'headers',
            file_response_headers(
                self.headers,
                as_attachment=self.as_attachment,
            ),
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
            # for mypy: it can't be `None` here
            assert media.schema  # noqa: S101
            media.schema = self.return_type.get_schema(Schema(), context)
        # We know that `FileBody` was a fake model, remove it:
        context.registries.schema.try_unregister(
            serializer.schema_generator.schema_name(self.return_type),
        )
        return response
