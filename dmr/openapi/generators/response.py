import dataclasses
from http import HTTPStatus
from typing import TYPE_CHECKING, Literal

from dmr.openapi.objects import (
    Header,
    MediaType,
    Reference,
    Response,
    Responses,
    Schema,
)

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata, ResponseSpec
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseGenerator:
    """Generator for OpenAPI ``Response`` objects."""

    _context: 'OpenAPIContext'

    def __call__(
        self,
        metadata: 'EndpointMetadata',
        serializer: type['BaseSerializer'],
    ) -> Responses:
        """Generate responses from response specs."""
        return {
            # Deletegate call to `ResponseSpec`, so it can change
            # how the spec is generated.
            str(status_code.value): response_spec.get_schema(
                metadata,
                serializer,
                self._context,
            )
            for status_code, response_spec in metadata.responses.items()
        }

    def get_schema(  # noqa: WPS211
        self,
        response_spec: 'ResponseSpec',
        metadata: 'EndpointMetadata',
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
        *,
        schema_field_name: Literal['schema', 'item_schema'] = 'schema',
        used_for_response: bool = True,
    ) -> Response:
        """
        Returns the OpenAPI schema for the response.

        Can be customized in ``ResponseSpec`` subclasses.
        """
        headers: dict[str, Header | Reference] = {}
        headers.update(self._get_headers(response_spec, serializer, context))
        headers.update(self._get_cookies(response_spec, serializer, context))

        return Response(
            description=(
                response_spec.description
                or HTTPStatus(response_spec.status_code).phrase
            ),
            links=response_spec.links,
            headers=headers or None,
            content=self._get_content(
                response_spec,
                serializer,
                context,
                metadata,
                schema_field_name=schema_field_name,
                used_for_response=used_for_response,
            ),
        )

    def _get_headers(
        self,
        response_spec: 'ResponseSpec',
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> dict[str, Header | Reference]:
        if not response_spec.headers:
            return {}

        return {
            name: Header(
                description=header_spec.description,
                deprecated=header_spec.deprecated or None,
                required=header_spec.required or None,
                schema=context.generators.schema(str, serializer),
            )
            for name, header_spec in response_spec.headers.items()
        }

    def _get_cookies(
        self,
        response_spec: 'ResponseSpec',
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> dict[str, Header | Reference]:
        # Import cycle:
        if not response_spec.cookies:
            return {}

        cookies: dict[str, Header | Reference] = {}
        for name, cookie_spec in response_spec.cookies.items():
            schema = context.generators.schema(str, serializer)
            # for mypy: `str` cannot return a reference, it is a primitive
            assert isinstance(schema, Schema)  # noqa: S101
            schema = dataclasses.replace(schema, example=f'{name}=123')

            cookies[f'Set-Cookie: {name}'] = Header(
                description=cookie_spec.description,
                required=cookie_spec.required or None,
                schema=schema,
            )
        return cookies

    def _get_content(  # noqa: WPS211
        self,
        response_spec: 'ResponseSpec',
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
        metadata: 'EndpointMetadata',
        *,
        schema_field_name: str,
        used_for_response: bool,
    ) -> dict[str, MediaType]:
        # Import cycle:
        from dmr.negotiation import get_conditional_types  # noqa: PLC0415

        return_types = (
            get_conditional_types(response_spec.return_type, ()) or {}
        )
        return {
            renderer.content_type: MediaType(
                **{  # type: ignore[arg-type]
                    schema_field_name: context.generators.schema(
                        return_types.get(
                            renderer.content_type,
                            response_spec.return_type,
                        ),
                        serializer,
                        used_for_response=used_for_response,
                    ),
                },
            )
            for renderer in metadata.renderers.values()
            if (
                not response_spec.limit_to_content_types
                or renderer.content_type in response_spec.limit_to_content_types
            )
        }
