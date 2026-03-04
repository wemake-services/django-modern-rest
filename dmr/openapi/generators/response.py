import dataclasses
from http import HTTPStatus
from typing import TYPE_CHECKING

from dmr.openapi.objects.header import Header
from dmr.openapi.objects.media_type import MediaType
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.response import Response
from dmr.openapi.objects.responses import Responses
from dmr.openapi.objects.schema import Schema

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata, ResponseSpec
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.renderers import Renderer
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
            str(status_code.value): self._generate_response(
                metadata.renderers,
                response_spec,
                serializer,
            )
            for status_code, response_spec in metadata.responses.items()
        }

    def _generate_response(
        self,
        renderers: dict[str, 'Renderer'],
        response_spec: 'ResponseSpec',
        serializer: type['BaseSerializer'],
    ) -> Response:
        headers: dict[str, Header | Reference] = {}
        headers.update(self._get_headers(response_spec, serializer))
        headers.update(self._get_cookies(response_spec, serializer))

        return Response(
            description=(
                response_spec.description
                or HTTPStatus(response_spec.status_code).phrase
            ),
            headers=headers or None,
            content=self._get_content(renderers, response_spec, serializer),
        )

    def _get_headers(
        self,
        response_spec: 'ResponseSpec',
        serializer: type['BaseSerializer'],
    ) -> dict[str, Header | Reference]:
        if not response_spec.headers:
            return {}

        return {
            name: Header(
                description=header_spec.description,
                deprecated=header_spec.deprecated or None,
                required=header_spec.required or None,
                schema=self._context.generators.schema(str, serializer),
            )
            for name, header_spec in response_spec.headers.items()
        }

    def _get_cookies(
        self,
        response_spec: 'ResponseSpec',
        serializer: type['BaseSerializer'],
    ) -> dict[str, Header | Reference]:
        if not response_spec.cookies:
            return {}

        cookies: dict[str, Header | Reference] = {}
        for name, cookie_spec in response_spec.cookies.items():
            schema = self._context.generators.schema(str, serializer)
            # for mypy: `str` cannot return a reference, it is a primitive
            assert isinstance(schema, Schema)  # noqa: S101
            schema = dataclasses.replace(schema, example=f'{name}=123')

            cookies[f'Set-Cookie: {name}'] = Header(
                description=cookie_spec.description,
                required=cookie_spec.required or None,
                schema=schema,
            )
        return cookies

    def _get_content(
        self,
        renderers: dict[str, 'Renderer'],
        response_spec: 'ResponseSpec',
        serializer: type['BaseSerializer'],
    ) -> dict[str, MediaType]:
        # Import cycle:
        from dmr.negotiation import get_conditional_types  # noqa: PLC0415

        return_types = get_conditional_types(response_spec.return_type) or {}
        return {
            renderer.content_type: MediaType(
                schema=self._context.generators.schema(
                    return_types.get(
                        renderer.content_type,
                        response_spec.return_type,
                    ),
                    serializer,
                    used_for_response=True,
                ),
            )
            for renderer in renderers.values()
            if (
                not response_spec.limit_to_content_types
                or renderer.content_type in response_spec.limit_to_content_types
            )
        }
