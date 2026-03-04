import dataclasses
from typing import TYPE_CHECKING, Any, TypeAlias

from dmr.openapi.objects.parameter import Parameter
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.request_body import RequestBody
from dmr.openapi.objects.schema import Schema

if TYPE_CHECKING:
    from dmr.components import ComponentParser
    from dmr.metadata import EndpointMetadata
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.objects.media_type import MediaType
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
        request_body: RequestBody | None = None

        for parser, parser_args in metadata.component_parsers:
            schema = self._call_component(
                parser,
                parser_args,
                metadata,
                serializer,
            )

            if isinstance(schema, RequestBody):
                request_body = self._merge_bodies(schema, request_body)
            elif isinstance(schema, list):  # pyright: ignore[reportUnnecessaryIsInstance]
                params_list.extend(schema)
            else:
                raise TypeError(
                    f'Returning {schema} from ComponentParser.get_schema '
                    'is not supported',
                )

        return request_body, params_list or None

    def _call_component(
        self,
        parser: type['ComponentParser'],
        parser_args: tuple[Any, ...],
        metadata: 'EndpointMetadata',
        serializer: type['BaseSerializer'],
    ) -> list[Parameter | Reference] | RequestBody:
        model = parser_args[0] if len(parser_args) == 1 else parser_args
        return parser.get_schema(
            model,
            schema=self._context.generators.schema(
                model,
                serializer,
                fake_schema=parser.generates_fake_schema,
            ),
            serializer=serializer,
            metadata=metadata,
            context=self._context,
        )

    def _merge_bodies(
        self,
        new_schema: RequestBody,
        schema: RequestBody | None,
    ) -> RequestBody:
        if schema is None:
            return new_schema
        new_content = self._merge_contents(new_schema, schema)

        return RequestBody(
            content=new_content,
            description=(
                (schema.description or '') + (new_schema.description or '')
            ),
            required=schema.required or new_schema.required,
        )

    def _merge_contents(
        self,
        new_schema: RequestBody,
        schema: RequestBody,
    ) -> dict[str, 'MediaType']:
        new_content: dict[str, MediaType] = {}
        for media_name, media_type in new_schema.content.items():
            media_items = [media_type.schema]
            existing_content = schema.content.get(media_name)
            # TODO: remove pragma after fixing conditional types
            if existing_content:  # pragma: no cover
                media_items.append(existing_content.schema)
            new_content[media_name] = dataclasses.replace(
                media_type,
                schema=Schema(all_of=media_items),
            )
        return new_content
