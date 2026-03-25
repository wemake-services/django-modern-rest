from http import HTTPMethod, HTTPStatus
from typing import Any, TypeAlias

import pydantic
import pytest
from dirty_equals import IsInstance
from django.http import HttpResponse

from dmr import (  # noqa: WPS235
    Body,
    Controller,
    Headers,
    Path,
    Query,
    ResponseSpec,
    modify,
    validate,
)
from dmr.components import (
    BodyComponent,
    HeadersComponent,
    PathComponent,
    QueryComponent,
)
from dmr.plugins.pydantic import PydanticSerializer

_ComponentTypes: TypeAlias = list[tuple[str, Any, tuple[Any, ...]]]


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
    Controller[PydanticSerializer],
):
    @modify()
    def get(self, parsed_query: Query[_QueryModel]) -> list[int]:
        raise NotImplementedError

    def post(self, parsed_query: Query[_QueryModel]) -> list[str]:
        raise NotImplementedError

    @validate(ResponseSpec(list[int], status_code=HTTPStatus.OK))
    def put(self, parsed_query: Query[_QueryModel]) -> HttpResponse:
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
    assert [
        (component.context_name, model, meta)
        for component, model, meta in endpoint.metadata.component_parsers
    ] == [('parsed_query', _QueryModel, (IsInstance(QueryComponent),))]


class _MultiComponentController(Controller[PydanticSerializer]):
    """Controller with endpoint-level components."""

    @modify()
    def get(
        self,
        parsed_query: Query[_QueryModel],
        parsed_headers: Headers[_HeadersModel],
        parsed_path: Path[_PathModel],
    ) -> list[int]:
        raise NotImplementedError

    def post(
        self,
        parsed_query: Query[_QueryModel],
        parsed_body: Body[_BodyModel],
        parsed_headers: Headers[_HeadersModel],
        parsed_path: Path[_PathModel],
    ) -> list[str]:
        raise NotImplementedError

    @validate(ResponseSpec(list[int], status_code=HTTPStatus.OK))
    def put(
        self,
        parsed_query: Query[_QueryModel],
        parsed_body: Body[_BodyModel],
        parsed_headers: Headers[_HeadersModel],
        parsed_path: Path[_PathModel],
    ) -> HttpResponse:
        raise NotImplementedError


def test_multiple_components_get() -> None:
    """Ensure GET endpoint has components without Body."""
    endpoint = _MultiComponentController.api_endpoints['GET']
    assert isinstance(endpoint.metadata.component_parsers, list)
    components: _ComponentTypes = [
        ('parsed_query', _QueryModel, (IsInstance(QueryComponent),)),
        ('parsed_headers', _HeadersModel, (IsInstance(HeadersComponent),)),
        ('parsed_path', _PathModel, (IsInstance(PathComponent),)),
    ]
    assert sorted(components) == sorted([
        (component.context_name, model, meta)
        for component, model, meta in endpoint.metadata.component_parsers
    ])


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
    components: _ComponentTypes = [
        ('parsed_query', _QueryModel, (IsInstance(QueryComponent),)),
        ('parsed_headers', _HeadersModel, (IsInstance(HeadersComponent),)),
        ('parsed_path', _PathModel, (IsInstance(PathComponent),)),
        ('parsed_body', _BodyModel, (IsInstance(BodyComponent),)),
    ]
    assert sorted(components) == sorted([
        (component.context_name, model, meta)
        for component, model, meta in endpoint.metadata.component_parsers
    ])
