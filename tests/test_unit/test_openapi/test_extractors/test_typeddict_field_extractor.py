from typing import Any, TypedDict

import pytest

from django_modern_rest.openapi.extractors.stdlib import TypedDictExtractor


class _BrokenAnnotations:
    """We change __annotations__ here."""


class _TestTypedDict(TypedDict):
    name: str
    age: int


class _TestTypedDictRequired(TypedDict, total=False):
    name: str
    age: int


@pytest.mark.parametrize(
    ('dict_class', 'expected_required'),
    [
        (_TestTypedDict, True),
        (_TestTypedDictRequired, False),
    ],
)
def test_typed_dict_extractor_fields(
    dict_class: type[dict[str, Any]],
    *,
    expected_required: bool,
) -> None:
    """Ensure TypedDictExtractor extracts fields correctly."""
    extractor = TypedDictExtractor()
    fields = extractor.extract_fields(dict_class)

    assert len(fields) == 2

    field_map = {field.name: field for field in fields}

    assert field_map['name'].annotation is str
    assert field_map['name'].extra_data['is_required'] is expected_required

    assert field_map['age'].annotation is int
    assert field_map['age'].extra_data['is_required'] is expected_required


def test_extract_fields_value_error() -> None:
    """Ensure extract_fields handles ValueError from get_type_hints."""
    extractor = TypedDictExtractor()

    _BrokenAnnotations.__annotations__ = 'not a dict'  # type: ignore[assignment]
    fields = extractor.extract_fields(_BrokenAnnotations)  # type: ignore[arg-type]

    assert fields == []


def test_extract_fields_type_error() -> None:
    """Ensure extract_fields handles TypeError from get_type_hints."""
    extractor = TypedDictExtractor()

    fields = extractor.extract_fields(1)  # type: ignore[arg-type]

    assert fields == []
