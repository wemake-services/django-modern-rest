import pydantic
import pytest
from django.urls import path

from dmr.controller import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _ResponseModel(pydantic.BaseModel):
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
    """Ensure that multiple cookies are handled."""
    with pytest.raises(
        ValueError,
        match='Different schemas under a single name: _ResponseModel',
    ):
        build_schema(
            Router(
                [
                    path('first', _FirstController.as_view()),
                    path('second', _SecondController.as_view()),
                ],
                prefix='/',
            ),
        )
