from http import HTTPMethod, HTTPStatus
from typing import Any

import pydantic
import pytest
from django.http import HttpResponse

from django_modern_rest import (  # noqa: WPS235
    Blueprint,
    Body,
    Headers,
    Path,
    Query,
    ResponseDescription,
    compose_blueprints,
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


class _GetBlueprint(
    Query[_QueryModel],
    Blueprint[PydanticSerializer],
):
    @modify()
    def get(self) -> list[int]:
        raise NotImplementedError


class _PostBlueprint(
    Body[_BodyModel],
    Headers[_HeadersModel],
    Blueprint[PydanticSerializer],
):
    @validate(ResponseDescription(list[int], status_code=HTTPStatus.OK))
    def post(self) -> HttpResponse:
        raise NotImplementedError


class _PutBlueprint(  # noqa: WPS215
    Query[_QueryModel],
    Body[_BodyModel],
    Path[_PathModel],
    Blueprint[PydanticSerializer],
):
    def put(self) -> dict[str, str]:
        raise NotImplementedError


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
def test_compose_blueprints_preserves_parsers(
    *,
    method: HTTPMethod,
    expected: Any,
) -> None:
    """Ensure composed blueprints preserve ``component_parsers``."""
    composed = compose_blueprints(
        _GetBlueprint,
        _PostBlueprint,
        _PutBlueprint,
    )

    endpoint = composed.api_endpoints[str(method)]
    assert endpoint.metadata.component_parsers == list(expected)
