"""Test that component_parsers are correctly stored in EndpointMetadata."""

import pydantic

from django_modern_rest import Body, Controller, Headers, Path, Query, modify
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _QueryModel(pydantic.BaseModel):
    search: str


class _BodyModel(pydantic.BaseModel):
    name: str


class _HeadersModel(pydantic.BaseModel):
    token: str


class _PathModel(pydantic.BaseModel):
    user_id: int


def test_no_components() -> None:
    """Ensure controller without components has empty component_parsers."""

    class _NoComponentsController(Controller[PydanticSerializer]):
        @modify()
        def get(self) -> list[int]:  # pragma: no cover
            return [1, 2, 3]

    endpoint = _NoComponentsController.api_endpoints['get']
    assert endpoint.metadata.component_parsers == []


def test_single_component_query() -> None:
    """Ensure controller with Query component has it in component_parsers."""

    class _QueryController(
        Query[_QueryModel],
        Controller[PydanticSerializer],
    ):
        @modify()
        def get(self) -> list[int]:  # pragma: no cover
            return [1, 2, 3]

    endpoint = _QueryController.api_endpoints['get']
    assert len(endpoint.metadata.component_parsers) == 1

    component_cls, type_args = endpoint.metadata.component_parsers[0]
    assert component_cls.__name__ == 'Query'
    assert type_args == (_QueryModel,)


def test_multiple_components() -> None:
    """Ensure controller has all multiple components in component_parsers."""

    class _MultiComponentController(  # noqa: WPS215
        Query[_QueryModel],
        Body[_BodyModel],
        Headers[_HeadersModel],
        Path[_PathModel],
        Controller[PydanticSerializer],
    ):
        @modify()
        def put(self) -> dict[str, str]:  # pragma: no cover
            return {'status': 'updated'}

    endpoint = _MultiComponentController.api_endpoints['put']
    assert len(endpoint.metadata.component_parsers) == 4

    component_names = {
        klass.__name__ for klass, _ in endpoint.metadata.component_parsers
    }
    assert component_names == {'Query', 'Body', 'Headers', 'Path'}

    component_dict = {
        klass.__name__: args
        for klass, args in endpoint.metadata.component_parsers
    }
    assert component_dict['Query'] == (_QueryModel,)
    assert component_dict['Body'] == (_BodyModel,)
    assert component_dict['Headers'] == (_HeadersModel,)
    assert component_dict['Path'] == (_PathModel,)


def test_parsers_shared_across_endpoints() -> None:  # noqa: WPS210
    """Ensure each endpoint has the same component_parsers from controller."""

    class _MultiMethodController(
        Query[_QueryModel],
        Controller[PydanticSerializer],
    ):
        @modify()
        def get(self) -> list[int]:  # pragma: no cover
            return [1, 2, 3]

        @modify()
        def post(self) -> dict[str, str]:  # pragma: no cover
            return {'status': 'ok'}

    get_endpoint = _MultiMethodController.api_endpoints['get']
    post_endpoint = _MultiMethodController.api_endpoints['post']

    assert len(get_endpoint.metadata.component_parsers) == 1
    assert len(post_endpoint.metadata.component_parsers) == 1

    get_component_cls, get_type_args = get_endpoint.metadata.component_parsers[
        0
    ]
    post_component_cls, post_type_args = (
        post_endpoint.metadata.component_parsers[0]
    )

    assert get_component_cls.__name__ == 'Query'
    assert post_component_cls.__name__ == 'Query'
    assert get_type_args == (_QueryModel,)
    assert post_type_args == (_QueryModel,)
