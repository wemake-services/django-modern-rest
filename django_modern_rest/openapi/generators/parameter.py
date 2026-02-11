import dataclasses
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

from django_modern_rest.openapi.extractors.finder import find_extractor
from django_modern_rest.openapi.objects.parameter import Parameter
from django_modern_rest.openapi.objects.reference import Reference

if TYPE_CHECKING:
    from django_modern_rest.metadata import ComponentParserSpec
    from django_modern_rest.openapi.core.context import OpenAPIContext

_CONTEXT_TO_IN: Final = MappingProxyType({
    'parsed_query': 'query',
    'parsed_path': 'path',
    'parsed_headers': 'header',
    'parsed_cookies': 'cookie',
})


@dataclasses.dataclass(frozen=True, slots=True)
class ParameterGenerator:
    """Generator for OpenAPI ``Parameter`` objects."""

    context: 'OpenAPIContext'

    def __call__(
        self,
        parsers: 'list[ComponentParserSpec]',
    ) -> list[Parameter | Reference] | None:
        """Generate parameters from parsers."""
        params_list: list[Parameter | Reference] = []

        for parser_cls, parser_args in parsers:
            param_in = _CONTEXT_TO_IN.get(parser_cls.context_name)

            if not param_in or not parser_args:
                continue

            params_list.extend(
                self._generate_from_type(
                    parser_args[0],
                    param_in,
                ),
            )

        return params_list or None

    def _generate_from_type(
        self,
        source_type: Any,
        param_in: str,
    ) -> list[Parameter | Reference]:
        extractor = find_extractor(source_type)

        params_list: list[Parameter | Reference] = []
        for field in extractor.extract_fields(source_type):
            required = field.extra_data.get('is_required', False)

            if param_in == 'path':
                required = True

            params_list.append(
                Parameter(
                    name=field.name,
                    param_in=param_in,
                    schema=self.context.generators.schema(
                        field.annotation,
                    ),
                    description=None
                    if field.kwarg_definition is None
                    else field.kwarg_definition.description,
                    required=required,
                ),
            )
        return params_list
