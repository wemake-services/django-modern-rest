from typing import Any, Final, final

import pytest
from pydantic import BaseModel, Field

from django_modern_rest.openapi.extractors.pydantic_extractor import (
    PydanticFieldExtractor,
)
from django_modern_rest.openapi.types import FieldDefinition, KwargDefinition

_EXAMPLE_NAME: Final = 'John Doe'
_MIN_LENGTH: Final = 2
_MAX_LENGTH: Final = 5
_ALIAS: Final = 'fullName'
_DESCRIPTION: Final = 'User full name'


@final
class _SimpleModel(BaseModel):
    name: str


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


@pytest.fixture
def extractor() -> PydanticFieldExtractor:
    """Fixture for PydanticFieldExtractor."""
    return PydanticFieldExtractor()


@pytest.mark.parametrize(
    'model_cls',
    [
        _SimpleModel,
        _DetailedModel,
        _NestedModel,
    ],
)
def test_is_supported_true(
    extractor: PydanticFieldExtractor,
    model_cls: type[BaseModel],
) -> None:
    """Ensure is_supported returns True for Pydantic models."""
    assert extractor.is_supported(model_cls)


@pytest.mark.parametrize(
    'unsupported_type',
    [
        int,
        'string',
        dict,
    ],
)
def test_is_supported_false(
    extractor: PydanticFieldExtractor,
    unsupported_type: Any,
) -> None:
    """Ensure is_supported returns False for non-Pydantic types."""
    assert not extractor.is_supported(unsupported_type)


def test_extract_with_kwargs(extractor: PydanticFieldExtractor) -> None:
    """Ensure extractors extract kwargs from fields."""
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
    """Ensure extractors handle default values and json_schema_extra."""
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
