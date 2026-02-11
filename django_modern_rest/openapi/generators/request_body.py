import dataclasses
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.media_type import MediaType
from django_modern_rest.openapi.objects.request_body import RequestBody

if TYPE_CHECKING:
    from django_modern_rest.metadata import ComponentParserSpec
    from django_modern_rest.openapi.core.context import OpenAPIContext
    from django_modern_rest.parsers import Parser


@dataclasses.dataclass(frozen=True, slots=True)
class RequestBodyGenerator:
    """Generator for OpenAPI ``RequestBody`` objects."""

    _context: 'OpenAPIContext'

    def __call__(
        self,
        parsers: 'list[ComponentParserSpec]',
        request_parsers: 'dict[str, Parser]',
    ) -> RequestBody | None:
        """Generate request body from parsers."""
        for parser, model in parsers:
            # TODO: Do we need enum for context name?
            if parser.context_name != 'parsed_body':
                continue

            parser_type = model[0]
            reference = self._context.generators.schema(parser_type)
            return RequestBody(
                content={
                    req_parser.content_type: MediaType(schema=reference)
                    for req_parser in request_parsers.values()
                },
                required=True,
            )
        return None
