from typing import Any, get_type_hints

from typing_extensions import is_typeddict, override

from django_modern_rest.openapi.extractors.base import FieldExtractor
from django_modern_rest.openapi.types import FieldDefinition


class TypedDictExtractor(FieldExtractor[type[dict[str, Any]]]):
    """Extract fields from TypedDicts."""

    @classmethod
    @override
    def is_supported(cls, source: Any) -> bool:
        return is_typeddict(source)

    @override
    def extract_fields(
        self,
        source: type[dict[str, Any]],
    ) -> list[FieldDefinition]:
        definitions: list[FieldDefinition] = []
        type_hints = get_type_hints(source)

        required_keys: frozenset[str] = getattr(
            source,
            '__required_keys__',
            frozenset(),
        )

        for name, annotation in type_hints.items():
            definitions.append(
                FieldDefinition(
                    name=name,
                    annotation=annotation,
                    extra_data={'is_required': name in required_keys},
                ),
            )
        return definitions
