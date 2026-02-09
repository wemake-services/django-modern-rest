from typing import Any, Final, Literal, final

import pytest
from pydantic import BaseModel, Field

from django_modern_rest.openapi.types import FieldDefinition, KwargDefinition
from django_modern_rest.plugins.pydantic import (
    PydanticFieldExtractor,
)

_EXAMPLE_NAME: Final = 'John Doe'
_MIN_LENGTH: Final = 2
_MAX_LENGTH: Final = 5
_ALIAS: Final = 'fullName'
_DESCRIPTION: Final = 'User full name'


@pytest.fixture
def extractor() -> PydanticFieldExtractor:
    """Fixtutre for generating ``PydanticFieldExtractor`` instance."""
    return PydanticFieldExtractor()


@final
class _SimpleModel(BaseModel):
    name: str
    status: Literal['active', 'pending']
    tags: list[str]
    metadata: dict[str, Any]


@final
class _DetailedModel(BaseModel):
    name: str = Field(
        ...,
        alias=_ALIAS,
        description=_DESCRIPTION,
        min_length=_MIN_LENGTH,
        max_length=_MAX_LENGTH,
        examples=[{'name': _EXAMPLE_NAME}],
    )


@final
class _NestedModel(BaseModel):
    child: _SimpleModel
    generic_field: list[_DetailedModel]


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        (_SimpleModel, True),
        (_DetailedModel, True),
        (_NestedModel, True),
        (int, False),
        ('string', False),
        (dict, False),
    ],
)
def test_is_supported(
    source: Any,
    *,
    expected: bool,
    extractor: PydanticFieldExtractor,
) -> None:
    """Ensure ``is_supported`` returns correct results for various types."""
    assert extractor.is_supported(source) is expected


def test_extract_with_kwargs(extractor: PydanticFieldExtractor) -> None:
    """Ensure extractors extract `kwargs` from fields."""
    definitions = extractor.extract_fields(_DetailedModel)

    assert len(definitions) == 1
    definition = definitions[0]

    assert isinstance(definition, FieldDefinition)
    assert isinstance(definition.kwarg_definition, KwargDefinition)

    kwargs = definition.kwarg_definition
    assert kwargs.default is None
    assert kwargs.min_length == _MIN_LENGTH
    assert kwargs.max_length == _MAX_LENGTH
    assert kwargs.examples == [{'name': _EXAMPLE_NAME}]


def test_extract_with_default_and_schema_extra(
    extractor: PydanticFieldExtractor,
) -> None:
    """Ensure extractors handle ``default`` values and ``json_schema_extra``."""
    extra_schema = {'example': 'data'}
    default_val = 18

    class _ModelWithDefault(BaseModel):
        age: int = Field(
            default=default_val,
            json_schema_extra=extra_schema,  # type: ignore[arg-type]
        )

    definitions = extractor.extract_fields(_ModelWithDefault)
    assert len(definitions) == 1
    definition = definitions[0]

    assert definition.default == default_val
    assert definition.kwarg_definition is not None
    assert definition.kwarg_definition.schema_extra == extra_schema


def test_extract_simple_types(extractor: PydanticFieldExtractor) -> None:
    """Ensure complex types like ``Literal`` and generics are extracted."""
    definitions = extractor.extract_fields(_SimpleModel)

    fields_map = {
        field_def.name: field_def.annotation for field_def in definitions
    }

    assert fields_map == {
        'name': str,
        'status': Literal['active', 'pending'],
        'tags': list[str],
        'metadata': dict[str, Any],
    }


def test_extract_nested_generics(extractor: PydanticFieldExtractor) -> None:
    """Ensure nested generic models are extracted."""
    definitions = extractor.extract_fields(_NestedModel)

    fields_map = {
        field_def.name: field_def.annotation for field_def in definitions
    }

    assert fields_map == {
        'child': _SimpleModel,
        'generic_field': list[_DetailedModel],
    }
