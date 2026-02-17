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


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseGenerator:
    """Generator for OpenAPI ``Response`` objects."""

    _context: 'OpenAPIContext'

    def __call__(self, metadata: 'EndpointMetadata') -> Responses:
        """Generate responses from response specs."""
        return {
            str(status_code.value): self._generate_response(
                metadata.renderers,
                response_spec,
            )
            for status_code, response_spec in metadata.responses.items()
        }

    def _generate_response(
        self,
        renderers: dict[str, 'Renderer'],
        response_spec: 'ResponseSpec',
    ) -> Response:
        headers: dict[str, Header | Reference] = {}
        headers.update(self._get_headers(response_spec))
        headers.update(self._get_cookies(response_spec))

        return Response(
            description=HTTPStatus(response_spec.status_code).phrase,
            headers=headers or None,
            content=self._get_content(renderers, response_spec),
        )

    def _get_headers(
        self,
        response_spec: 'ResponseSpec',
    ) -> dict[str, Header | Reference]:
        if not response_spec.headers:
            return {}

        return {
            name: Header(
                description=header_spec.description,
                deprecated=header_spec.deprecated or None,
                required=header_spec.required or None,
                schema=self._context.generators.schema(str),
            )
            for name, header_spec in response_spec.headers.items()
        }

    def _get_cookies(
        self,
        response_spec: 'ResponseSpec',
    ) -> dict[str, Header | Reference]:
        if not response_spec.cookies:
            return {}

        cookies: dict[str, Header | Reference] = {}
        for name, cookie_spec in response_spec.cookies.items():
            schema = self._context.generators.schema(str)
            if isinstance(schema, Schema):
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
    ) -> dict[str, MediaType]:
        return {
            renderer.content_type: MediaType(
                schema=self._context.generators.schema(
                    response_spec.return_type,
                ),
            )
            for renderer in renderers.values()
        }
