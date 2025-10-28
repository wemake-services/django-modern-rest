from http import HTTPMethod, HTTPStatus
from typing import Any

import pydantic
import pytest
from django.http import HttpResponse

from django_modern_rest import (  # noqa: WPS235
    Body,
    Controller,
    Headers,
    Path,
    Query,
    ResponseDescription,
    compose_controllers,
    modify,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _QueryModel(pydantic.BaseModel):
    search: str


class _BodyModel(pydantic.BaseModel):
    name: str


class _HeadersModel(pydantic.BaseModel):
    token: str


class _PathModel(pydantic.BaseModel):
    user_id: int


class _GetController(
    Query[_QueryModel],
    Controller[PydanticSerializer],
):
    @modify()
    def get(self) -> list[int]:
        raise NotImplementedError


class _PostController(
    Body[_BodyModel],
    Headers[_HeadersModel],
    Controller[PydanticSerializer],
):
    @validate(ResponseDescription(list[int], status_code=HTTPStatus.OK))
    def post(self) -> HttpResponse:
        raise NotImplementedError


class _PutController(  # noqa: WPS215
    Query[_QueryModel],
    Body[_BodyModel],
    Path[_PathModel],
    Controller[PydanticSerializer],
):
    def put(self) -> dict[str, str]:
        raise NotImplementedError


ComposedController = compose_controllers(
    _GetController,
    _PostController,
    _PutController,
)


@pytest.mark.parametrize(
    ('method', 'expected'),
    [
        (
            HTTPMethod.GET,
            ((Query[_QueryModel], (_QueryModel,)),),
        ),
        (
            HTTPMethod.POST,
            (
                (Body[_BodyModel], (_BodyModel,)),
                (Headers[_HeadersModel], (_HeadersModel,)),
            ),
        ),
        (
            HTTPMethod.PUT,
            (
                (Query[_QueryModel], (_QueryModel,)),
                (Body[_BodyModel], (_BodyModel,)),
                (Path[_PathModel], (_PathModel,)),
            ),
        ),
    ],
)
def test_compose_controllers_preserves_parsers(
    *,
    method: HTTPMethod,
    expected: Any,
) -> None:
    """Ensure composed controller preserves component_parsers."""
    endpoint = ComposedController.api_endpoints[str(method).lower()]
    assert endpoint.metadata.component_parsers == list(expected)
