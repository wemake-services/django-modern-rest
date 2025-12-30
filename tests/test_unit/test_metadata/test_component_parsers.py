from http import HTTPMethod, HTTPStatus

import pydantic
import pytest
from django.http import HttpResponse

from django_modern_rest import (  # noqa: WPS235
    Blueprint,
    Body,
    Controller,
    Headers,
    Path,
    Query,
    ResponseSpec,
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


class _NoComponentsController(Controller[PydanticSerializer]):
    @modify()
    def get(self) -> list[int]:
        raise NotImplementedError

    def post(self) -> list[str]:
        raise NotImplementedError

    @validate(ResponseSpec(list[int], status_code=HTTPStatus.OK))
    def put(self) -> HttpResponse:
        raise NotImplementedError


@pytest.mark.parametrize(
    'method',
    [HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT],
)
def test_no_components(
    *,
    method: HTTPMethod,
) -> None:
    """Ensure controller without components has empty component_parsers."""
    endpoint = _NoComponentsController.api_endpoints[str(method)]
    assert endpoint.metadata.component_parsers == []


class _QueryController(
    Query[_QueryModel],
    Controller[PydanticSerializer],
):
    @modify()
    def get(self) -> list[int]:
        raise NotImplementedError

    def post(self) -> list[str]:
        raise NotImplementedError

    @validate(ResponseSpec(list[int], status_code=HTTPStatus.OK))
    def put(self) -> HttpResponse:
        raise NotImplementedError


@pytest.mark.parametrize(
    'method',
    [HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT],
)
def test_single_component_query(
    *,
    method: HTTPMethod,
) -> None:
    """Ensure controller with Query component has it in component_parsers."""
    endpoint = _QueryController.api_endpoints[str(method)]
    assert endpoint.metadata.component_parsers == [
        (
            Query[_QueryModel],
            (_QueryModel,),
        ),
    ]


class _GetBlueprint(  # noqa: WPS215
    Query[_QueryModel],
    Headers[_HeadersModel],
    Path[_PathModel],
    Blueprint[PydanticSerializer],
):
    """Blueprint for GET (method without Body)."""

    @modify()
    def get(self) -> list[int]:
        raise NotImplementedError


class _PostBlueprint(  # noqa: WPS215
    Query[_QueryModel],
    Body[_BodyModel],
    Headers[_HeadersModel],
    Path[_PathModel],
    Blueprint[PydanticSerializer],
):
    """Blueprint for POST/PUT (methods with Body)."""

    def post(self) -> list[str]:
        raise NotImplementedError

    @validate(ResponseSpec(list[int], status_code=HTTPStatus.OK))
    def put(self) -> HttpResponse:
        raise NotImplementedError


class _MultiComponentController(Controller[PydanticSerializer]):
    blueprints = [_GetBlueprint, _PostBlueprint]


def test_multiple_components_get() -> None:
    """Ensure GET endpoint has components without Body."""
    endpoint = _MultiComponentController.api_endpoints['GET']
    assert isinstance(endpoint.metadata.component_parsers, list)
    assert tuple(endpoint.metadata.component_parsers) == (
        (Query[_QueryModel], (_QueryModel,)),
        (Headers[_HeadersModel], (_HeadersModel,)),
        (Path[_PathModel], (_PathModel,)),
    )


@pytest.mark.parametrize(
    'method',
    [HTTPMethod.POST, HTTPMethod.PUT],
)
def test_multiple_components_with_body(
    *,
    method: HTTPMethod,
) -> None:
    """Ensure controller has all multiple components in component_parsers."""
    endpoint = _MultiComponentController.api_endpoints[str(method)]
    assert isinstance(endpoint.metadata.component_parsers, list)
    assert tuple(endpoint.metadata.component_parsers) == (
        (Query[_QueryModel], (_QueryModel,)),
        (Body[_BodyModel], (_BodyModel,)),
        (Headers[_HeadersModel], (_HeadersModel,)),
        (Path[_PathModel], (_PathModel,)),
    )
