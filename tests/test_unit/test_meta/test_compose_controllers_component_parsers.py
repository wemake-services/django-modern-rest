import pydantic

from django_modern_rest import (
    Body,
    Controller,
    Headers,
    Path,
    Query,
    compose_controllers,
    modify,
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


def test_compose_controllers_preserves_parsers() -> None:  # noqa: WPS210
    """Ensure composed controller preserves component_parsers."""

    class _GetController(
        Query[_QueryModel],
        Controller[PydanticSerializer],
    ):
        @modify()
        def get(self) -> list[int]:  # pragma: no cover
            return [1, 2, 3]

    class _PostController(
        Body[_BodyModel],
        Headers[_HeadersModel],
        Controller[PydanticSerializer],
    ):
        @modify()
        def post(self) -> dict[str, str]:  # pragma: no cover
            return {'status': 'created'}

    class _PutController(  # noqa: WPS215
        Query[_QueryModel],
        Body[_BodyModel],
        Path[_PathModel],
        Controller[PydanticSerializer],
    ):
        @modify()
        def put(self) -> dict[str, str]:  # pragma: no cover
            return {'status': 'updated'}

    ComposedController = compose_controllers(  # noqa: N806
        _GetController,
        _PostController,
        _PutController,
    )

    get_endpoint = ComposedController.api_endpoints['get']
    assert len(get_endpoint.metadata.component_parsers) == 1
    component_cls, type_args = get_endpoint.metadata.component_parsers[0]
    assert component_cls is Query[_QueryModel]
    assert type_args == (_QueryModel,)

    post_endpoint = ComposedController.api_endpoints['post']
    assert len(post_endpoint.metadata.component_parsers) == 2
    post_component_dict = {
        klass.__name__: args
        for klass, args in post_endpoint.metadata.component_parsers
    }
    assert post_component_dict['Body'] == (_BodyModel,)
    assert post_component_dict['Headers'] == (_HeadersModel,)

    put_endpoint = ComposedController.api_endpoints['put']
    assert len(put_endpoint.metadata.component_parsers) == 3

    put_component_dict = {
        klass.__name__: args
        for klass, args in put_endpoint.metadata.component_parsers
    }
    assert put_component_dict['Query'] == (_QueryModel,)
    assert put_component_dict['Body'] == (_BodyModel,)
    assert put_component_dict['Path'] == (_PathModel,)
