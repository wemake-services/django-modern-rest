from typing import Final

import pydantic
import pytest
from django.urls import path, register_converter
from inline_snapshot import snapshot

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router

_YEAR_CONVERTER: Final = 'dmr_year'
_INVALID_CONVERTER: Final = 'dmr_invalid'


class _YearConverter:
    """Maps a 4-digit year and declares an integer OpenAPI schema."""

    regex = '[0-9]{4}'
    __dmr_converter_schema__ = int

    def to_python(self, value: str) -> int:  # noqa: WPS110
        """Parse the captured path segment."""
        raise NotImplementedError

    def to_url(self, value: int) -> str:  # noqa: WPS110
        """Render the year back into a URL segment."""
        raise NotImplementedError


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
        raise NotImplementedError

    def to_url(self, value: str) -> str:  # noqa: WPS110
        """Render the segment back into a URL."""
        raise NotImplementedError


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
    assert operation['parameters'] == snapshot([
        {
            'deprecated': False,
            'name': 'year',
            'in': 'path',
            'schema': {'type': 'integer', 'title': 'Year'},
            'required': True,
        },
    ])


def test_converter_schema_invalid() -> None:
    """Ensure an invalid ``__dmr_converter_schema__`` fails spec validation."""
    openapi_exceptions = pytest.importorskip(
        'openapi_spec_validator.validation.exceptions',
    )
    register_converter(_InvalidConverter, _INVALID_CONVERTER)

    with pytest.raises(
        openapi_exceptions.OpenAPIValidationError,
        match='minItems',
    ):
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
