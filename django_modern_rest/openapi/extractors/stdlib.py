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

    @override
    def extract_fields(
        self,
        source: type[dict[str, Any]],
    ) -> list[FieldDefinition]:
        try:
            type_hints = get_type_hints(source)
        except (ValueError, TypeError):
            return []

        required_keys, optional_keys = self._get_keys(source)
        return self._create_definitions(
            type_hints,
            required_keys,
            optional_keys,
        )

    def _create_definitions(
        self,
        type_hints: dict[str, Any],
        required_keys: frozenset[str],
        optional_keys: frozenset[str],
    ) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name=name,
                annotation=annotation,
                extra_data={'is_required': name in required_keys},
            )
            for name, annotation in type_hints.items()
            if name in required_keys or name in optional_keys
        ]

    def _get_keys(
        self,
        source: type[dict[str, Any]],
    ) -> tuple[frozenset[str], frozenset[str]]:
        required_keys: frozenset[str] = getattr(
            source,
            '__required_keys__',
            frozenset(),
        )
        optional_keys: frozenset[str] = getattr(
            source,
            '__optional_keys__',
            frozenset(),
        )
        return required_keys, optional_keys
