import pydantic
import pytest
from django.urls import path
from inline_snapshot import snapshot

from dmr.controller import Controller
from dmr.openapi import OpenAPIContext, build_schema
from dmr.openapi.objects import OpenAPIType, Schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _ResponseModel(pydantic.BaseModel):  # pyright: ignore[reportRedeclaration]
    first: int


class _FirstController(Controller[PydanticSerializer]):
    def post(self) -> _ResponseModel:
        raise NotImplementedError


class _ResponseModel(pydantic.BaseModel):  # type: ignore[no-redef]
    second: str


class _SecondController(Controller[PydanticSerializer]):
    def put(self) -> _ResponseModel:
        raise NotImplementedError


def test_duplicated_schema() -> None:
    """Ensure that duplicated schemas raise."""
    with pytest.raises(
        ValueError,
        match='Different schemas under a single name: _ResponseModel',
    ):
        build_schema(
            Router(
                '/',
                [
                    path('first', _FirstController.as_view()),
                    path('second', _SecondController.as_view()),
                ],
            ),
        )


class _ResponseModel(pydantic.BaseModel):  # type: ignore[no-redef]
    second: str
    model_config = pydantic.ConfigDict(title='_CustomResponseModel')


class _ThirdController(Controller[PydanticSerializer]):
    def put(self) -> _ResponseModel:
        raise NotImplementedError


def test_renamed_schema() -> None:
    """Ensure that renamed schemas work."""
    build_schema(
        Router(
            '/',
            [
                path('first', _FirstController.as_view()),
                path('third', _ThirdController.as_view()),
            ],
        ),
    )


def test_resolve_ref_with_siblings(
    openapi_context: OpenAPIContext,
) -> None:
    """Keywords next to ``$ref`` annotate one usage, not the component."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1491
    title = 'Address'
    component = Schema(
        type=OpenAPIType.OBJECT,
        description='The component itself',
        title=title,
    )
    registry = openapi_context.registries.schema
    registry.register(title, component)

    resolved = registry.maybe_resolve_reference(
        Schema(
            ref='#/components/schemas/Address',
            default={'city': 'Moscow'},
            description='Where the user lives',
        ),
    )

    assert resolved == snapshot(
        Schema(
            type=OpenAPIType.OBJECT,
            title=title,
            description='Where the user lives',
            default={'city': 'Moscow'},
        ),
    )
    assert registry.schemas[title] is component


def test_resolve_pure_ref(openapi_context: OpenAPIContext) -> None:
    """A ``Schema`` without siblings resolves to the component itself."""
    registry = openapi_context.registries.schema
    component = Schema(type=OpenAPIType.STRING)
    registry.register('Plain', component)

    resolved = registry.maybe_resolve_reference(
        Schema(ref='#/components/schemas/Plain'),
    )

    assert resolved is component


def test_resolve_schema_without_ref(openapi_context: OpenAPIContext) -> None:
    """A flat ``Schema`` needs no resolution at all."""
    registry = openapi_context.registries.schema
    flat = Schema(type=OpenAPIType.BOOLEAN)

    assert registry.maybe_resolve_reference(flat) is flat
