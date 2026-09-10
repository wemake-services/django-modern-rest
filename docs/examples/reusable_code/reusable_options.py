from collections.abc import Sequence
from http import HTTPStatus
from typing import ClassVar

from dmr import Controller, ResponseSpec
from dmr.errors import ErrorModel
from dmr.plugins.pydantic import PydanticSerializer


class MyBaseController(Controller[PydanticSerializer]):
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(ErrorModel, status_code=HTTPStatus.NOT_FOUND),
    )

    def get(self) -> str:
        return 'reusable'


class MyController(MyBaseController):
    # This works only because `responses` is annotated in the parent class.
    # Without that annotation type-checkers infer the type of `responses`
    # from the parent's value, which is a tuple of exactly one item,
    # and this assignment fails with:
    # Incompatible types in assignment (expression has type
    # "tuple[ResponseSpec, ResponseSpec]", base class "MyBaseController"
    # defined the type as "tuple[ResponseSpec]")
    responses = (
        *MyBaseController.responses,
        ResponseSpec(ErrorModel, status_code=HTTPStatus.CONFLICT),
    )
