from typing import Any, NotRequired, Required

import pytest
from typing_extensions import ReadOnly, TypedDict

from django_modern_rest.openapi.extractors.stdlib import TypedDictExtractor


@pytest.fixture
def extractor() -> TypedDictExtractor:
    """Fixtutre for generating extractor instance."""
    return TypedDictExtractor()


class _BrokenAnnotations:
    """We change __annotations__ here."""


class _TestTypedDict(TypedDict):
    name: str
    age: int


class _TestTypedDictRequired(TypedDict, total=False):
    name: str
    age: int


class _Parent(TypedDict):
    parent_field: int


class _Child(_Parent):
    child_field: str


class _Mixed(TypedDict):
    req: Required[int]
    not_req: NotRequired[str]
    implicit_req: bool


class _ClosedTypedDict(TypedDict, closed=True):  # type: ignore[call-arg]
    field: int


class _ClosedExtraTypedDict(TypedDict, extra_items=int):  # type: ignore[call-arg]
    field: str


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
    extractor: TypedDictExtractor,
) -> None:
    """Ensure TypedDictExtractor extracts fields correctly."""
    fields = extractor.extract_fields(dict_class)

    assert len(fields) == 2

    field_map = {field.name: field for field in fields}

    assert field_map['name'].annotation is str
    assert field_map['name'].extra_data['is_required'] is expected_required

    assert field_map['age'].annotation is int
    assert field_map['age'].extra_data['is_required'] is expected_required


def test_extract_fields_broken_annotations(
    extractor: TypedDictExtractor,
) -> None:
    """Ensure extract_fields handles errors from get_type_hints."""
    _BrokenAnnotations.__annotations__ = 'not a dict'  # type: ignore[assignment]

    assert extractor.extract_fields(_BrokenAnnotations) == []  # type: ignore[arg-type]


def test_extract_fields_type_error(extractor: TypedDictExtractor) -> None:
    """Ensure extract_fields handles TypeError from get_type_hints."""
    assert extractor.extract_fields(1) == []  # type: ignore[arg-type]


def test_typed_dict_inheritance(extractor: TypedDictExtractor) -> None:
    """Ensure TypedDictExtractor extracts fields from inherited TypedDicts."""
    fields = extractor.extract_fields(_Child)  # type: ignore[arg-type]

    assert len(fields) == 2
    field_map = {field.name: field for field in fields}

    assert field_map['parent_field'].annotation is int
    assert field_map['child_field'].annotation is str


def test_typed_dict_required_not_required(
    extractor: TypedDictExtractor,
) -> None:
    """Ensure TypedDictExtractor handles Required and NotRequired."""
    fields = extractor.extract_fields(_Mixed)  # type: ignore[arg-type]

    field_map = {field.name: field for field in fields}

    assert field_map['req'].extra_data['is_required'] is True
    assert field_map['req'].annotation is int
    assert field_map['not_req'].extra_data['is_required'] is False
    assert field_map['not_req'].annotation is str
    assert field_map['implicit_req'].extra_data['is_required'] is True
    assert field_map['implicit_req'].annotation is bool


def test_typed_dict_readonly(extractor: TypedDictExtractor) -> None:
    """Ensure TypedDictExtractor handles ReadOnly."""

    class _ReadOnly(TypedDict):
        readonly_field: ReadOnly[int]
        normal_field: str

    fields = extractor.extract_fields(_ReadOnly)  # type: ignore[arg-type]
    field_map = {field.name: field for field in fields}
    assert 'readonly_field' in field_map
    assert 'normal_field' in field_map


@pytest.mark.parametrize(
    'extra_type_dict',
    [_ClosedTypedDict, _ClosedExtraTypedDict],
)
def test_typed_dict_extra(
    extra_type_dict: type[dict[str, Any]],
    *,
    extractor: TypedDictExtractor,
) -> None:
    """Ensure TypedDictExtractor work with extra items (PEP 728)."""
    fields = extractor.extract_fields(extra_type_dict)

    assert len(fields) == 1
    assert fields[0].name == 'field'
