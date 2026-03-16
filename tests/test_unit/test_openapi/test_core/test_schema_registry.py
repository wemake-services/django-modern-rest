import pydantic
import pytest
from django.urls import path

from dmr.controller import Controller
from dmr.openapi import OpenAPIContext, build_schema
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


def test_try_unregister_schema(openapi_context: OpenAPIContext) -> None:
    """Ensure that removing non existent schema works."""
    openapi_context.registries.schema.try_unregister('missing')
    openapi_context.registries.schema.try_unregister(None)
