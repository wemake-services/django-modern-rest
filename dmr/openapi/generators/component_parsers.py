import dataclasses
from typing import TYPE_CHECKING, TypeAlias

from dmr.openapi.objects.parameter import Parameter
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.request_body import RequestBody

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer


_RequestBody: TypeAlias = RequestBody | Reference | None
_RequestParameters: TypeAlias = list[Parameter | Reference] | None


@dataclasses.dataclass(frozen=True, slots=True)
class ComponentParserGenerator:
    """Generator for OpenAPI ``Parameter`` objects."""

    _context: 'OpenAPIContext'

    def __call__(
        self,
        metadata: 'EndpointMetadata',
        serializer: type['BaseSerializer'],
    ) -> tuple[_RequestBody, _RequestParameters]:
        """Generate parameters from parsers."""
        params_list: list[Parameter | Reference] = []
        request_body: RequestBody | Reference | None = None

        for parser, parser_args in metadata.component_parsers:
            schema = parser.get_schema(
                schema=self._context.generators.schema(
                    (parser_args[0] if len(parser_args) == 1 else parser_args),
                    serializer,
                    fake_schema=parser.generates_fake_schema,
                ),
                serializer=serializer,
                metadata=metadata,
                context=self._context,
            )

            if isinstance(schema, RequestBody):
                # TODO: merge bodies instead
                assert request_body is None, 'Overriding existing request_body'  # noqa: S101
                request_body = schema
            elif isinstance(schema, list):  # pyright: ignore[reportUnnecessaryIsInstance]
                params_list.extend(schema)
            else:
                raise TypeError(
                    f'Returning {schema} from ComponentParser.get_schema '
                    'is not supported',
                )

        return request_body, params_list or None
