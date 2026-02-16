import dataclasses
from http import HTTPStatus
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.header import Header
from django_modern_rest.openapi.objects.media_type import MediaType
from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.openapi.objects.response import Response
from django_modern_rest.openapi.objects.responses import Responses
from django_modern_rest.openapi.objects.schema import Schema

if TYPE_CHECKING:
    from django_modern_rest.metadata import EndpointMetadata, ResponseSpec
    from django_modern_rest.openapi.core.context import OpenAPIContext
    from django_modern_rest.parsers import Parser


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseGenerator:
    """Generator for OpenAPI ``Response`` objects."""

    _context: 'OpenAPIContext'

    def __call__(self, metadata: 'EndpointMetadata') -> Responses:
        """Generate responses from response specs."""
        return {
            str(status_code.value): self._generate_response(
                metadata.parsers,
                response_spec,
            )
            for status_code, response_spec in metadata.responses.items()
        }

    def _generate_response(
        self,
        parsers: 'dict[str, Parser]',
        response_spec: 'ResponseSpec',
    ) -> Response:
        headers: dict[str, Header | Reference] = {}
        if response_spec.headers:
            for name, header_spec in response_spec.headers.items():
                headers[name] = Header(
                    description=header_spec.description,
                    deprecated=header_spec.deprecated,
                    required=header_spec.required,
                    schema=self._context.generators.schema(str),
                )

        if response_spec.cookies:
            for name, cookie_spec in response_spec.cookies.items():
                schema = self._context.generators.schema(str)
                if isinstance(schema, Schema):
                    schema = dataclasses.replace(schema, example=f'{name}=123')

                headers[f'Set-Cookie: {name}'] = Header(
                    description=cookie_spec.description,
                    required=cookie_spec.required,
                    schema=schema,
                )

        return Response(
            description=HTTPStatus(response_spec.status_code).phrase,
            headers=headers or None,
            content={
                parser.content_type: MediaType(
                    schema=self._context.generators.schema(
                        response_spec.return_type,
                    ),
                )
                for parser in parsers.values()
            },
        )
