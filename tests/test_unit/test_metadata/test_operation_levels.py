from http import HTTPMethod, HTTPStatus
from types import MappingProxyType
from typing import Any, Final, TypeAlias

import pytest
from django.http import HttpResponse
from django.urls import path

from dmr import Controller, ResponseSpec, modify, validate
from dmr.openapi import build_schema
from dmr.openapi.objects import (
    Callback,
    ExternalDocumentation,
    PathItem,
    Reference,
    Server,
)
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.types import EMPTY

_CallbackMapping: TypeAlias = MappingProxyType[str, Callback | Reference]

_CONTROLLER_DOCS: Final = ExternalDocumentation(
    url='https://example.com/controller',
)
_ENDPOINT_DOCS: Final = ExternalDocumentation(
    url='https://example.com/endpoint',
)
_CONTROLLER_CALLBACKS: Final[_CallbackMapping] = MappingProxyType({
    'onEvent': Callback({'{$request.body#/url}': PathItem()}),
})
_ENDPOINT_CALLBACKS: Final[_CallbackMapping] = MappingProxyType({
    'onDone': Reference(ref='#/components/callbacks/onDone'),
})


def _operation(
    controller_cls: type[Controller[PydanticSerializer]],
    method: HTTPMethod,
    **router_kwargs: Any,
) -> dict[str, Any]:
    schema = build_schema(
        Router(
            'api/',
            [path('user/', controller_cls.as_view())],
            **router_kwargs,
        ),
    ).convert()
    return schema['paths']['/api/user/'][method.lower()]  # type: ignore[no-any-return]


def _path_item(
    controller_cls: type[Controller[PydanticSerializer]],
) -> dict[str, Any]:
    schema = build_schema(
        Router('api/', [path('user/', controller_cls.as_view())]),
    ).convert()
    return schema['paths']['/api/user/']  # type: ignore[no-any-return]


def _extension_keys(openapi_object: dict[str, Any]) -> list[str]:
    return [key for key in openapi_object if key.startswith('x-')]


# `deprecated`:


def test_deprecated_not_set() -> None:
    """Nothing is set: metadata keeps `EMPTY` and the schema has no flag."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

        @modify()
        def post(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.deprecated is EMPTY
    assert _Controller.api_endpoints['POST'].metadata.deprecated is EMPTY
    assert 'deprecated' not in _operation(_Controller, HTTPMethod.GET)
    assert 'deprecated' not in _operation(_Controller, HTTPMethod.POST)


def test_deprecated_controller_level() -> None:
    """Controller level `deprecated` applies to all endpoints."""

    class _Controller(Controller[PydanticSerializer]):
        deprecated = True

        def get(self) -> str:
            raise NotImplementedError

        @modify()
        def post(self) -> str:
            raise NotImplementedError

        @validate(ResponseSpec(str, status_code=HTTPStatus.OK))
        def put(self) -> HttpResponse:
            raise NotImplementedError

    for method in (HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT):
        assert _Controller.api_endpoints[method].metadata.deprecated is True
        assert _operation(_Controller, method)['deprecated'] is True


def test_deprecated_endpoint_level() -> None:
    """Endpoint level `deprecated` wins, even when it is `False`."""

    class _Controller(Controller[PydanticSerializer]):
        deprecated = True

        @modify(deprecated=False)
        def get(self) -> str:
            raise NotImplementedError

        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            deprecated=False,
        )
        def put(self) -> HttpResponse:
            raise NotImplementedError

    assert (
        _Controller.api_endpoints[HTTPMethod.GET].metadata.deprecated is False
    )
    assert (
        _Controller.api_endpoints[HTTPMethod.PUT].metadata.deprecated is False
    )
    assert 'deprecated' not in _operation(_Controller, HTTPMethod.GET)
    assert 'deprecated' not in _operation(_Controller, HTTPMethod.PUT)


def test_deprecated_router_is_the_last_level() -> None:
    """Router `deprecated` is only used when other levels are not set."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

        @modify(deprecated=False)
        def post(self) -> str:
            raise NotImplementedError

    assert (
        _operation(_Controller, HTTPMethod.GET, deprecated=True)['deprecated']
        is True
    )
    assert 'deprecated' not in _operation(
        _Controller,
        HTTPMethod.POST,
        deprecated=True,
    )


def test_deprecated_controller_overrides_router() -> None:
    """Controller `deprecated=False` disables the router value."""

    class _Controller(Controller[PydanticSerializer]):
        deprecated = False

        def get(self) -> str:
            raise NotImplementedError

    assert 'deprecated' not in _operation(
        _Controller,
        HTTPMethod.GET,
        deprecated=True,
    )


# `external_docs`:


def test_external_docs_not_set() -> None:
    """Nothing is set: metadata has `None` and the schema has no docs."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

        @modify()
        def post(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.external_docs is None
    assert _Controller.api_endpoints['POST'].metadata.external_docs is None
    assert 'externalDocs' not in _operation(_Controller, HTTPMethod.GET)


def test_external_docs_controller_level() -> None:
    """Controller level `external_docs` applies to all endpoints."""

    class _Controller(Controller[PydanticSerializer]):
        external_docs = _CONTROLLER_DOCS

        def get(self) -> str:
            raise NotImplementedError

        @modify()
        def post(self) -> str:
            raise NotImplementedError

        @validate(ResponseSpec(str, status_code=HTTPStatus.OK))
        def put(self) -> HttpResponse:
            raise NotImplementedError

    for method in (HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT):
        metadata = _Controller.api_endpoints[method].metadata
        assert metadata.external_docs is _CONTROLLER_DOCS
    assert _operation(_Controller, HTTPMethod.GET)['externalDocs'] == {
        'url': 'https://example.com/controller',
    }


def test_external_docs_endpoint_level() -> None:
    """Endpoint level `external_docs` wins, `None` disables it."""

    class _Controller(Controller[PydanticSerializer]):
        external_docs = _CONTROLLER_DOCS

        @modify(external_docs=_ENDPOINT_DOCS)
        def get(self) -> str:
            raise NotImplementedError

        @modify(external_docs=None)
        def post(self) -> str:
            raise NotImplementedError

        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            external_docs=None,
        )
        def put(self) -> HttpResponse:
            raise NotImplementedError

    endpoints = _Controller.api_endpoints
    assert endpoints['GET'].metadata.external_docs is _ENDPOINT_DOCS
    assert endpoints['POST'].metadata.external_docs is None
    assert endpoints['PUT'].metadata.external_docs is None
    assert _operation(_Controller, HTTPMethod.GET)['externalDocs'] == {
        'url': 'https://example.com/endpoint',
    }
    assert 'externalDocs' not in _operation(_Controller, HTTPMethod.POST)


# `callbacks`:


def test_callbacks_not_set() -> None:
    """Nothing is set: metadata has `None` and the schema has no callbacks."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

        @modify()
        def post(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.callbacks is None
    assert _Controller.api_endpoints['POST'].metadata.callbacks is None
    assert 'callbacks' not in _operation(_Controller, HTTPMethod.GET)


def test_callbacks_controller_level() -> None:
    """Controller level `callbacks` apply to all endpoints as a new dict."""

    class _Controller(Controller[PydanticSerializer]):
        callbacks = _CONTROLLER_CALLBACKS

        def get(self) -> str:
            raise NotImplementedError

        @modify()
        def post(self) -> str:
            raise NotImplementedError

        @validate(ResponseSpec(str, status_code=HTTPStatus.OK))
        def put(self) -> HttpResponse:
            raise NotImplementedError

    for method in (HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT):
        metadata = _Controller.api_endpoints[method].metadata
        assert metadata.callbacks == _CONTROLLER_CALLBACKS
        assert isinstance(metadata.callbacks, dict)
    assert _operation(_Controller, HTTPMethod.GET)['callbacks'] == {
        'onEvent': {'{$request.body#/url}': {}},
    }


def test_callbacks_endpoint_level() -> None:
    """Endpoint level `callbacks` win, `None` disables them."""

    class _Controller(Controller[PydanticSerializer]):
        callbacks = _CONTROLLER_CALLBACKS

        @modify(callbacks=_ENDPOINT_CALLBACKS)
        def get(self) -> str:
            raise NotImplementedError

        @modify(callbacks=None)
        def post(self) -> str:
            raise NotImplementedError

        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            callbacks=None,
        )
        def put(self) -> HttpResponse:
            raise NotImplementedError

    endpoints = _Controller.api_endpoints
    assert endpoints['GET'].metadata.callbacks == _ENDPOINT_CALLBACKS
    assert endpoints['POST'].metadata.callbacks is None
    assert endpoints['PUT'].metadata.callbacks is None
    assert _operation(_Controller, HTTPMethod.GET)['callbacks'] == {
        'onDone': {'$ref': '#/components/callbacks/onDone'},
    }
    assert 'callbacks' not in _operation(_Controller, HTTPMethod.POST)


@pytest.mark.parametrize('empty', [{}, ()])
def test_callbacks_explicit_empty(empty: Any) -> None:
    """Explicit empty endpoint callbacks disable the controller ones."""

    class _Controller(Controller[PydanticSerializer]):
        callbacks = _CONTROLLER_CALLBACKS

        @modify(callbacks=empty)
        def get(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.callbacks == {}


# `servers`:

_CONTROLLER_SERVERS: Final = (Server(url='https://example.com'),)
_ENDPOINT_SERVERS: Final = (Server(url='https://dev.example.com'),)


def test_servers_not_set() -> None:
    """Nothing is set: metadata has `None` and the schema has no servers."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.servers is None
    assert 'servers' not in _operation(_Controller, HTTPMethod.GET)


def test_servers_controller_level() -> None:
    """Controller `servers` are resolved into every operation, not path item."""

    class _Controller(Controller[PydanticSerializer]):
        servers = _CONTROLLER_SERVERS

        def get(self) -> str:
            raise NotImplementedError

        @modify()
        def post(self) -> str:
            raise NotImplementedError

        @validate(ResponseSpec(str, status_code=HTTPStatus.OK))
        def put(self) -> HttpResponse:
            raise NotImplementedError

    schema = build_schema(
        Router('api/', [path('user/', _Controller.as_view())]),
    ).convert()
    path_item = schema['paths']['/api/user/']
    assert 'servers' not in path_item
    for method in (HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT):
        metadata = _Controller.api_endpoints[method].metadata
        assert metadata.servers == list(_CONTROLLER_SERVERS)
        assert path_item[method.lower()]['servers'] == [
            {'url': 'https://example.com'},
        ]


def test_servers_endpoint_level() -> None:
    """Endpoint level `servers` win, `None` disables them."""

    class _Controller(Controller[PydanticSerializer]):
        servers = _CONTROLLER_SERVERS

        @modify(servers=_ENDPOINT_SERVERS)
        def get(self) -> str:
            raise NotImplementedError

        @modify(servers=None)
        def post(self) -> str:
            raise NotImplementedError

        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            servers=None,
        )
        def put(self) -> HttpResponse:
            raise NotImplementedError

    endpoints = _Controller.api_endpoints
    assert endpoints['GET'].metadata.servers == list(_ENDPOINT_SERVERS)
    assert endpoints['POST'].metadata.servers is None
    assert endpoints['PUT'].metadata.servers is None
    assert _operation(_Controller, HTTPMethod.GET)['servers'] == [
        {'url': 'https://dev.example.com'},
    ]
    assert 'servers' not in _operation(_Controller, HTTPMethod.POST)


# `x_extensions`:

_CONTROLLER_EXTENSIONS: Final = MappingProxyType({
    'x-owner': 'users-team',
})
_ENDPOINT_EXTENSIONS: Final = MappingProxyType({
    'x-audience': 'public',
    'x-rate-limit': 100,
})


def test_x_extensions_not_set() -> None:
    """Nothing is set: metadata has `None` and the schema has no `x-` keys."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

        @modify()
        def post(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.x_extensions is None
    assert _Controller.api_endpoints['POST'].metadata.x_extensions is None
    assert _extension_keys(_operation(_Controller, HTTPMethod.GET)) == []
    assert _extension_keys(_path_item(_Controller)) == []


def test_x_extensions_controller_level() -> None:
    """Controller `x_extensions` describe the path item, not operations."""

    class _Controller(Controller[PydanticSerializer]):
        x_extensions = _CONTROLLER_EXTENSIONS

        def get(self) -> str:
            raise NotImplementedError

        @modify()
        def post(self) -> str:
            raise NotImplementedError

        @validate(ResponseSpec(str, status_code=HTTPStatus.OK))
        def put(self) -> HttpResponse:
            raise NotImplementedError

    for method in (HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT):
        assert _Controller.api_endpoints[method].metadata.x_extensions is None
        assert _extension_keys(_operation(_Controller, method)) == []
    path_item = _path_item(_Controller)
    assert _extension_keys(path_item) == ['x-owner']
    assert path_item['x-owner'] == 'users-team'


def test_x_extensions_endpoint_level() -> None:
    """Endpoint `x_extensions` describe the operation, never the path item."""

    class _Controller(Controller[PydanticSerializer]):
        x_extensions = _CONTROLLER_EXTENSIONS

        @modify(x_extensions=_ENDPOINT_EXTENSIONS)
        def get(self) -> str:
            raise NotImplementedError

        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            x_extensions=_ENDPOINT_EXTENSIONS,
        )
        def put(self) -> HttpResponse:
            raise NotImplementedError

    for method in (HTTPMethod.GET, HTTPMethod.PUT):
        metadata = _Controller.api_endpoints[method].metadata
        assert metadata.x_extensions == _ENDPOINT_EXTENSIONS
        assert isinstance(metadata.x_extensions, dict)
        # Never merged with the controller value:
        operation = _operation(_Controller, method)
        assert _extension_keys(operation) == ['x-audience', 'x-rate-limit']
    assert _extension_keys(_path_item(_Controller)) == ['x-owner']


def test_x_extensions_explicit_empty() -> None:
    """Explicit empty endpoint extensions are taken literally."""

    class _Controller(Controller[PydanticSerializer]):
        x_extensions = _CONTROLLER_EXTENSIONS

        @modify(x_extensions={})
        def get(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.x_extensions == {}
    assert _extension_keys(_operation(_Controller, HTTPMethod.GET)) == []
