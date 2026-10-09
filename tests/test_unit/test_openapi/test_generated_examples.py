from collections.abc import Callable, Sequence
from typing import Annotated, Any, final

import pydantic
import pytest
from django.conf import LazySettings
from django.urls import path
from inline_snapshot import snapshot
from polyfactory.field_meta import FieldMeta
from typing_extensions import override

from dmr import Body, Controller
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.openapi.mappers.example import generate_example, set_generated_example
from dmr.openapi.objects import Schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.plugins.pydantic.schema import PydanticSchemaGenerator
from dmr.routing import Router
from dmr.serializer import BaseSchemaGenerator
from dmr.settings import Settings
from dmr.types import EMPTY


class _UserController(Controller[PydanticSerializer]):
    def post(self, parsed_body: Body[dict[str, Any]]) -> str:
        raise NotImplementedError


def _build_schema(openapi_version: str) -> dict[str, Any]:
    return build_schema(
        Router('api/v1/', [path('user/', _UserController.as_view())]),
        config=OpenAPIConfig(
            title='Examples',
            version='1.0.0',
            openapi_version=openapi_version,
        ),
    ).convert()


def _inline_body_schema(dumped: dict[str, Any]) -> Any:
    """Inline schemas go through the generated schema code path."""
    operation = dumped['paths']['/api/v1/user/']['post']
    return operation['requestBody']['content']['application/json']['schema']


def _referenced_schema(dumped: dict[str, Any]) -> Any:
    """Registered components go through the reference code path."""
    return dumped['components']['schemas']['ErrorModel']


@pytest.mark.parametrize('openapi_version', ['3.1.0', '3.2.0'])
@pytest.mark.parametrize(
    'find_schema',
    [_inline_body_schema, _referenced_schema],
)
def test_generated_examples_keyword(
    settings: LazySettings,
    *,
    find_schema: Callable[[dict[str, Any]], Any],
    openapi_version: str,
) -> None:
    """Ensure that generated examples always use JSON Schema ``examples``."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    schema = find_schema(_build_schema(openapi_version))

    assert schema['examples']
    assert 'example' not in schema


def test_disabled_examples_write_nothing(settings: LazySettings) -> None:
    """Ensure that we don't write ``examples: [null]`` when disabled."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: EMPTY}

    schema = _inline_body_schema(_build_schema('3.2.0'))

    assert 'example' not in schema
    assert 'examples' not in schema


class _NoneController(Controller[PydanticSerializer]):
    def get(self) -> None:
        raise NotImplementedError


def test_generated_none_example(*, settings: LazySettings) -> None:
    """Ensure that generated ``None`` examples are not dropped."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1626
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    schema = build_schema(
        Router('api/v1/', [path('none/', _NoneController.as_view())]),
    ).convert()

    operation = schema['paths']['/api/v1/none/']['get']
    response = operation['responses']['200']
    assert response['content']['application/json']['schema'] == snapshot({
        'type': 'null',
        'examples': [None],
    })


def test_generate_example_none(*, settings: LazySettings) -> None:
    """Ensure that ``None`` is a generated example, not a missing one."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    assert generate_example(None, PydanticSerializer) is None


def test_generate_example_disabled(*, settings: LazySettings) -> None:
    """Ensure that ``EMPTY`` is returned when examples are disabled."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: EMPTY}

    assert generate_example(None, PydanticSerializer) is EMPTY


@pytest.mark.parametrize(
    ('example', 'expected_examples'),
    [
        (None, [None]),
        (0, [0]),
        ('', ['']),
        (EMPTY, None),
    ],
)
def test_set_generated_example(
    *,
    example: Any,
    expected_examples: list[Any] | None,
) -> None:
    """Ensure that only ``EMPTY`` examples are skipped."""
    assert (
        set_generated_example(Schema(), example).examples == expected_examples
    )


class _NoneExampleModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(json_schema_extra={'example': None})

    name: str | None


class _NoneExampleController(Controller[PydanticSerializer]):
    def post(self, parsed_body: Body[_NoneExampleModel]) -> str:
        raise NotImplementedError


def test_none_example_is_kept(*, settings: LazySettings) -> None:
    """Ensure that ``example: null`` is not replaced with generated ones."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1619
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    schema = build_schema(
        Router('api/v1/', [path('user/', _NoneExampleController.as_view())]),
    ).convert()

    model_schema = schema['components']['schemas']['_NoneExampleModel']
    assert model_schema['example'] is None
    assert 'examples' not in model_schema


def test_no_field_examples_by_default() -> None:
    """Ensure that fields have no examples, unless a serializer finds them."""
    field_meta = FieldMeta.from_type(annotation=str, name='username')

    assert not BaseSchemaGenerator.field_examples(field_meta)


@final
class _CustomExamplesGenerator(PydanticSchemaGenerator):
    @override
    @classmethod
    def field_examples(cls, field_meta: FieldMeta) -> Sequence[Any]:
        # Custom serializers can find field examples however they want:
        if field_meta.name == 'username':
            return ['custom']
        return super().field_examples(field_meta)


@final
class _CustomExamplesSerializer(PydanticSerializer):
    schema_generator = _CustomExamplesGenerator


class _CustomAccount(pydantic.BaseModel):
    username: str
    bio: Annotated[str, pydantic.Field(examples=['Hello'])]


class _CustomAccountController(Controller[_CustomExamplesSerializer]):
    def get(self) -> _CustomAccount:
        raise NotImplementedError


def test_custom_field_examples(*, settings: LazySettings) -> None:
    """Ensure that serializers can provide their own field examples."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1639
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    schema = build_schema(
        Router(
            'api/v1/',
            [path('account/', _CustomAccountController.as_view())],
        ),
    ).convert()

    assert schema['components']['schemas']['_CustomAccount'] == snapshot({
        'properties': {
            'username': {'type': 'string', 'title': 'Username'},
            'bio': {'type': 'string', 'title': 'Bio', 'examples': ['Hello']},
        },
        'type': 'object',
        'required': ['username', 'bio'],
        'title': '_CustomAccount',
        'examples': [{'username': 'custom', 'bio': 'Hello'}],
    })
