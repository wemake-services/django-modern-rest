import dataclasses
from http import HTTPStatus
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.media_type import MediaType
from django_modern_rest.openapi.objects.response import Response
from django_modern_rest.openapi.objects.responses import Responses

if TYPE_CHECKING:
    from django_modern_rest.metadata import ResponseSpec
    from django_modern_rest.openapi.core.context import OpenAPIContext
    from django_modern_rest.parsers import Parser


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseGenerator:
    """Generator for OpenAPI ``Response`` objects."""

    context: 'OpenAPIContext'

    def __call__(
        self,
        responses: dict[HTTPStatus, 'ResponseSpec'],
        request_parsers: 'dict[str, type[Parser]]',
    ) -> Responses:
        """Generate responses from response specs."""
        return {
            str(status_code.value): Response(
                description=status_code.phrase,
                content={
                    req_parser.content_type: MediaType(
                        schema=self.context.generators.schema(
                            response_spec.return_type,
                        ),
                    )
                    for req_parser in request_parsers.values()
                },
            )
            for status_code, response_spec in responses.items()
        }
