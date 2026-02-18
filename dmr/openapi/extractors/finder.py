from typing import Any

from dmr.openapi.extractors import FieldExtractor


def find_extractor(source_type: Any) -> FieldExtractor[Any]:
    """Find a field extractor for the given source type."""
    for extractor in FieldExtractor.registry:
        if extractor.is_supported(source_type):
            return extractor()
    raise ValueError(f'Field extractor for {source_type} not found')
