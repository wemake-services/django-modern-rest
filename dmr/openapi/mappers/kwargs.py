import contextlib
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar

from dmr.openapi.objects.enums import OpenAPIFormat

if TYPE_CHECKING:
    from dmr.openapi.objects.schema import Schema
    from dmr.openapi.types import KwargDefinition


class KwargMapper:
    """
    Class for mapping ``KwargDefinition`` to OpenAPI ``Schema``.

    This class is responsible for converting model-specific constraints
    into OpenAPI-compliant schema attributes.
    """

    __slots__ = ()

    # Public API:
    mapping: ClassVar[Mapping[str, str]] = {
        'content_encoding': 'content_encoding',
        'default': 'default',
        'title': 'title',
        'description': 'description',
        'const': 'const',
        'gt': 'exclusive_minimum',
        'ge': 'minimum',
        'lt': 'exclusive_maximum',
        'le': 'maximum',
        'multiple_of': 'multiple_of',
        'min_items': 'min_items',
        'max_items': 'max_items',
        'min_length': 'min_length',
        'max_length': 'max_length',
        'pattern': 'pattern',
        'format': 'format',
        'enum': 'enum',
        'read_only': 'read_only',
        'examples': 'examples',
        'external_docs': 'external_docs',
    }

    def __call__(
        self,
        schema: 'Schema',
        kwarg_definition: 'KwargDefinition',
    ) -> dict[str, Any]:
        """
        Extract updates for the schema from the kwarg definition.

        Args:
            schema: The schema object to be updated.
            kwarg_definition: Data container with constraints.

        """
        updates: dict[str, Any] = {}
        for kwarg_field, schema_field in self.mapping.items():
            kwarg_value = getattr(kwarg_definition, kwarg_field)
            if kwarg_value is None:
                continue

            if kwarg_field == 'format':
                with contextlib.suppress(ValueError):
                    kwarg_value = OpenAPIFormat(kwarg_value)

            updates[schema_field] = kwarg_value

        if kwarg_definition.schema_extra:
            updates.update(kwarg_definition.schema_extra)

        return updates
