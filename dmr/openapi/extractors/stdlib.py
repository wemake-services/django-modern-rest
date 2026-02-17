from typing import Any

from typing_extensions import get_type_hints, is_typeddict, override

from django_modern_rest.openapi.extractors.base import FieldExtractor
from django_modern_rest.openapi.types import FieldDefinition


class TypedDictExtractor(FieldExtractor[type[dict[str, Any]]]):
    """Extract fields from TypedDicts."""

    @classmethod
    @override
    def is_supported(cls, source: Any) -> bool:
        return is_typeddict(source)

    # TODO: What do we do with __extra_items__ here?
    @override
    def extract_fields(
        self,
        source: type[dict[str, Any]],
    ) -> list[FieldDefinition]:
        definitions: list[FieldDefinition] = []
        try:
            type_hints = get_type_hints(source)
        except (ValueError, TypeError, AttributeError):
            return definitions

        # TODO: Do we need to handle __optional_keys__ explicitly here?
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
