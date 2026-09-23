import dataclasses
from http import HTTPStatus
from operator import attrgetter
from typing import TYPE_CHECKING, Literal

from dmr.openapi.mappers.example import generate_example, set_generated_example
from dmr.openapi.objects import (
    Header,
    MediaType,
    Reference,
    Response,
    Responses,
    Schema,
)

if TYPE_CHECKING:
    from dmr.controller import Controller
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
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> Responses:
        """
        Generate responses from response specs.

        .. versionchanged:: 0.16.0
            Now accepts *controller_cls* parameter instead of *serializer*.

        """
        return {
            # Delegate call to `ResponseSpec`, so it can change
            # how the spec is generated.
            str(status_code.value): response_spec.get_schema(
                metadata,
                controller_cls,
                self._context,
            )
            # Sorted by status code, not by the definition order:
            for status_code, response_spec in sorted(
                metadata.responses.items(),
            )
        }

    def get_schema(
        self,
        response_spec: 'ResponseSpec',
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
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
        headers.update(
            self._get_headers(
                response_spec,
                controller_cls.serializer,
                context,
            ),
        )
        headers.update(
            self._get_cookies(
                response_spec,
                controller_cls.serializer,
                context,
            ),
        )

        return Response(
            description=(
                HTTPStatus(response_spec.status_code).phrase
                if response_spec.description is None
                else str(response_spec.description)
            ),
            summary=(
                None
                if response_spec.summary is None
                else str(response_spec.summary)
            ),
            links=(
                None
                if response_spec.links is None
                else dict(response_spec.links)
            ),
            # Sorted by header name, not by the definition order:
            headers=dict(sorted(headers.items())) or None,
            content=self._get_content(
                response_spec,
                controller_cls.serializer,
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
                description=(
                    None
                    if header_spec.description is None
                    else str(header_spec.description)
                ),
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
            # A `Set-Cookie` value is `name=value`, so we only generate
            # the value part. `replace` copies the schema, so the example
            # does not land on the shared `str` one:
            cookie_value = generate_example(str, serializer)
            schema = set_generated_example(
                dataclasses.replace(schema),
                None if cookie_value is None else f'{name}={cookie_value}',
            )

            cookies[f'Set-Cookie: {name}'] = Header(
                description=(
                    None
                    if cookie_spec.description is None
                    else str(cookie_spec.description)
                ),
                required=cookie_spec.required or None,
                schema=schema,
            )
        return cookies

    def _get_content(
        self,
        response_spec: 'ResponseSpec',
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
        metadata: 'EndpointMetadata',
        *,
        schema_field_name: str,
        used_for_response: bool,
    ) -> dict[str, MediaType | Reference]:
        # Import cycle:
        from dmr.internal.negotiation import (  # noqa: PLC0415
            get_conditional_types,
        )

        return_types = (
            get_conditional_types(response_spec.return_type, ()) or {}
        )
        return {
            # Sorted by content type, not by the renderers order:
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
            for renderer in sorted(
                metadata.renderers.values(),
                key=attrgetter('content_type'),
            )
            if (
                not response_spec.limit_to_content_types
                or renderer.content_type in response_spec.limit_to_content_types
            )
        }
