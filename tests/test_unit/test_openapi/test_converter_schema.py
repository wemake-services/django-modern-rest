from typing import Final

import pydantic
import pytest
from django.urls import path, register_converter

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router

OpenAPIValidationError = pytest.importorskip(
    'openapi_spec_validator.validation.exceptions',
).OpenAPIValidationError

_YEAR_CONVERTER: Final = 'dmr_year'
_INVALID_CONVERTER: Final = 'dmr_invalid'


class _YearConverter:
    """Maps a 4-digit year and declares an integer OpenAPI schema."""

    regex = '[0-9]{4}'
    __dmr_converter_schema__ = int

    def to_python(self, value: str) -> int:  # noqa: WPS110
        """Parse the captured path segment."""
        return int(value)

    def to_url(self, value: int) -> str:  # noqa: WPS110
        """Render the year back into a URL segment."""
        return str(value)


class _InvalidSchemaType(pydantic.BaseModel):
    """Type whose generated schema fails OpenAPI spec validation."""

    model_config = pydantic.ConfigDict(
        json_schema_extra={'minItems': -1},
    )


class _InvalidConverter:
    """Custom converter whose declared schema fails spec validation."""

    regex = '[0-9]+'
    __dmr_converter_schema__ = _InvalidSchemaType

    def to_python(self, value: str) -> str:  # noqa: WPS110
        """Return the captured path segment unchanged."""
        return value

    def to_url(self, value: str) -> str:  # noqa: WPS110
        """Render the segment back into a URL."""
        return value


class _ArticleController(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


def test_converter_schema_valid() -> None:
    """Ensure custom converters honor ``__dmr_converter_schema__``."""
    register_converter(_YearConverter, _YEAR_CONVERTER)
    schema = build_schema(
        Router(
            'api/',
            [
                path(
                    f'articles/<{_YEAR_CONVERTER}:year>/',
                    _ArticleController.as_view(),
                ),
            ],
        ),
    ).convert()

    operation = schema['paths']['/api/articles/{year}/']['get']
    year_schema = None
    for parameter in operation['parameters']:
        if parameter['name'] == 'year':
            year_schema = parameter['schema']
            break
    assert year_schema is not None
    assert year_schema['type'] == 'integer'


def test_converter_schema_invalid() -> None:
    """Ensure an invalid ``__dmr_converter_schema__`` fails spec validation."""
    register_converter(_InvalidConverter, _INVALID_CONVERTER)

    with pytest.raises(OpenAPIValidationError):
        build_schema(
            Router(
                'api/',
                [
                    path(
                        f'items/<{_INVALID_CONVERTER}:item_id>/',
                        _ArticleController.as_view(),
                    ),
                ],
            ),
        ).convert()
