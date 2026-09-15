import dataclasses
import json
import sys
import textwrap
from http import HTTPStatus
from typing import Any, Final, TypeAlias, TypeVar, final

import pydantic
import pytest
from dirty_equals import IsInstance
from django.http import HttpResponse
from typing_extensions import TypeAliasType, TypedDict

from dmr import (  # noqa: WPS235
    Body,
    Controller,
    Cookies,
    FileMetadata,
    Headers,
    Path,
    Query,
)
from dmr.components import (  # noqa: WPS235
    BodyComponent,
    CookiesComponent,
    FileMetadataComponent,
    HeadersComponent,
    PathComponent,
    QueryComponent,
)
from dmr.endpoint import Endpoint
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory
from dmr.types import unwrap_type_alias

_ComponentType: TypeAlias = tuple[str, Any, tuple[Any, ...]]
_ComponentTypes: TypeAlias = list[_ComponentType]

_Serializers: TypeAlias = list[Any]
serializers: Final[_Serializers] = [PydanticSerializer, PydanticFastSerializer]

try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pass  # do nothing then :(  # noqa: WPS420
else:
    serializers.append(MsgspecSerializer)


@final
class _QueryModel(pydantic.BaseModel):
    search: str


@final
class _BodyModel(pydantic.BaseModel):
    name: str


@final
class _HeadersModel(pydantic.BaseModel):
    token: str


@final
class _PathModel(pydantic.BaseModel):
    user_id: int


@final
class _CookiesModel(pydantic.BaseModel):
    session: str


@final
class _FileModel(pydantic.BaseModel):
    size: int


@final
class _FilesModel(pydantic.BaseModel):
    receipt: _FileModel


# Old-style aliases, they are just regular assignments in runtime:
_ExplicitQuery: TypeAlias = Query[_QueryModel]
_ExplicitBody: TypeAlias = Body[_BodyModel]
_ExplicitHeaders: TypeAlias = Headers[_HeadersModel]
_ExplicitPath: TypeAlias = Path[_PathModel]
_ExplicitCookies: TypeAlias = Cookies[_CookiesModel]
_ExplicitFiles: TypeAlias = FileMetadata[_FilesModel]

# `TypeAliasType` aliases, they are lazy objects that hide the real type.
# This is the only way to get them on Python 3.11,
# it also produces a different type than the `type X = Y` syntax does:
_LazyQuery = TypeAliasType('_LazyQuery', Query[_QueryModel])
_LazyBody = TypeAliasType('_LazyBody', Body[_BodyModel])
_LazyHeaders = TypeAliasType('_LazyHeaders', Headers[_HeadersModel])
_LazyPath = TypeAliasType('_LazyPath', Path[_PathModel])
_LazyCookies = TypeAliasType('_LazyCookies', Cookies[_CookiesModel])
_LazyFiles = TypeAliasType('_LazyFiles', FileMetadata[_FilesModel])

# Aliases of aliases and generic aliases must be unwrapped as well:
_NestedBody = TypeAliasType('_NestedBody', _LazyBody)

_ModelT = TypeVar('_ModelT')
_GenericBody = TypeAliasType(
    '_GenericBody',
    Body[_ModelT],
    type_params=(_ModelT,),
)

_ALL_COMPONENTS: Final[tuple[_ComponentType, ...]] = (
    ('parsed_query', _QueryModel, (IsInstance(QueryComponent),)),
    ('parsed_body', _BodyModel, (IsInstance(BodyComponent),)),
    ('parsed_headers', _HeadersModel, (IsInstance(HeadersComponent),)),
    ('parsed_path', _PathModel, (IsInstance(PathComponent),)),
    ('parsed_cookies', _CookiesModel, (IsInstance(CookiesComponent),)),
    (
        'parsed_file_metadata',
        _FilesModel,
        (IsInstance(FileMetadataComponent),),
    ),
)

_ONLY_BODY: Final[tuple[_ComponentType, ...]] = (
    ('parsed_body', _BodyModel, (IsInstance(BodyComponent),)),
)

#: More nested aliases than `dmr` is willing to unwrap.
_TOO_MANY_ALIASES: Final = 20


def _parsed_components(endpoint: Endpoint) -> _ComponentTypes:
    return sorted(
        (component.context_name, model, meta)
        for component, model, meta in endpoint.metadata.component_parsers
    )


@final
class _ExplicitAliasController(Controller[PydanticSerializer]):
    parsers = (MultiPartParser(),)

    def post(  # noqa: WPS211
        self,
        parsed_query: _ExplicitQuery,
        parsed_body: _ExplicitBody,
        parsed_headers: _ExplicitHeaders,
        parsed_path: _ExplicitPath,
        parsed_cookies: _ExplicitCookies,
        parsed_file_metadata: _ExplicitFiles,
    ) -> str:
        raise NotImplementedError


@final
class _LazyAliasController(Controller[PydanticSerializer]):
    parsers = (MultiPartParser(),)

    def post(  # noqa: WPS211
        self,
        parsed_query: _LazyQuery,
        parsed_body: _LazyBody,
        parsed_headers: _LazyHeaders,
        parsed_path: _LazyPath,
        parsed_cookies: _LazyCookies,
        parsed_file_metadata: _LazyFiles,
    ) -> str:
        raise NotImplementedError


@pytest.mark.parametrize(
    'controller',
    [_ExplicitAliasController, _LazyAliasController],
)
def test_aliased_components(
    *,
    controller: type[Controller[Any]],
) -> None:
    """Ensures that all components can be hidden behind a type alias."""
    endpoint = controller.api_endpoints['POST']

    assert _parsed_components(endpoint) == sorted(_ALL_COMPONENTS)


@final
class _NestedAliasController(Controller[PydanticSerializer]):
    def post(self, parsed_body: _NestedBody) -> str:
        raise NotImplementedError


@final
class _GenericAliasController(Controller[PydanticSerializer]):
    def post(self, parsed_body: _GenericBody[_BodyModel]) -> str:
        raise NotImplementedError


@pytest.mark.parametrize(
    'controller',
    [_NestedAliasController, _GenericAliasController],
)
def test_indirect_alias_component(
    *,
    controller: type[Controller[Any]],
) -> None:
    """Ensures that nested and subscripted generic aliases are unwrapped."""
    endpoint = controller.api_endpoints['POST']

    assert _parsed_components(endpoint) == sorted(_ONLY_BODY)


_NATIVE_ALIASES: Final = textwrap.dedent(
    """
    type _NativeQuery = Query[_QueryModel]
    type _NativeBody = Body[_BodyModel]
    type _NativeHeaders = Headers[_HeadersModel]
    type _NativePath = Path[_PathModel]
    type _NativeCookies = Cookies[_CookiesModel]
    type _NativeFiles = FileMetadata[_FilesModel]

    type _NativeGenericBody[_ModelT] = Body[_ModelT]

    class _NativeAliasController(Controller[PydanticSerializer]):
        parsers = (MultiPartParser(),)

        def post(
            self,
            parsed_query: _NativeQuery,
            parsed_body: _NativeBody,
            parsed_headers: _NativeHeaders,
            parsed_path: _NativePath,
            parsed_cookies: _NativeCookies,
            parsed_file_metadata: _NativeFiles,
        ) -> str:
            raise NotImplementedError

    class _NativeGenericController(Controller[PydanticSerializer]):
        def post(self, parsed_body: _NativeGenericBody[_BodyModel]) -> str:
            raise NotImplementedError
    """,
)


def _exec_native_aliases() -> dict[str, Any]:
    namespace = globals().copy()  # noqa: WPS421
    exec(_NATIVE_ALIASES, namespace)  # noqa: S102, WPS421
    return namespace


@pytest.mark.skipif(
    sys.version_info < (3, 12),
    reason='`type X = Y` syntax requires Python 3.12 or higher',
)
def test_native_aliased_components() -> None:
    """Ensures that `type X = Y` aliases work for all components."""
    controller = _exec_native_aliases()['_NativeAliasController']
    endpoint = controller.api_endpoints['POST']

    assert _parsed_components(endpoint) == sorted(_ALL_COMPONENTS)


@pytest.mark.skipif(
    sys.version_info < (3, 12),
    reason='`type X[T] = Y` syntax requires Python 3.12 or higher',
)
def test_native_generic_alias_component() -> None:
    """Ensures that subscripted generic aliases are unwrapped."""
    controller = _exec_native_aliases()['_NativeGenericController']
    endpoint = controller.api_endpoints['POST']

    assert _parsed_components(endpoint) == sorted(_ONLY_BODY)


# Serializer agnostic models, all our serializers understand them:


@dataclasses.dataclass
class _User:
    name: str


class _Filter(TypedDict):
    search: str


class _UserId(TypedDict):
    user_id: int


_AliasedBodyArg = TypeAliasType('_AliasedBodyArg', Body[_User])
_AliasedQueryArg = TypeAliasType('_AliasedQueryArg', Query[_Filter])
_AliasedPathArg = TypeAliasType('_AliasedPathArg', Path[_UserId])
_AliasedCookiesArg = TypeAliasType(
    '_AliasedCookiesArg',
    Cookies[dict[str, str]],
)


@pytest.mark.parametrize('serializer', serializers)
def test_aliased_components_are_parsed(
    dmr_rf: DMRRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that aliased components are parsed by all serializers."""

    class _Controller(Controller[serializer]):  # type: ignore[valid-type]
        def post(
            self,
            parsed_body: _AliasedBodyArg,
            parsed_query: _AliasedQueryArg,
            parsed_path: _AliasedPathArg,
            parsed_cookies: _AliasedCookiesArg,
        ) -> str:
            assert parsed_query == {'search': 'aliases'}
            assert parsed_path == {'user_id': 1}
            assert parsed_cookies == {'session': 'unique'}
            return parsed_body.name

    request = dmr_rf.post('/whatever/?search=aliases', data={'name': 'dmr'})
    request.COOKIES = {'session': 'unique'}

    response = _Controller.as_view()(request, user_id=1)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == 'dmr'


def test_unwrap_regular_type() -> None:
    """Ensures that anything that is not an alias is returned as is."""
    assert unwrap_type_alias(_BodyModel) is _BodyModel
    assert unwrap_type_alias(Body[_BodyModel]) == Body[_BodyModel]


# Type checkers only allow `TypeAliasType` to build real aliases,
# we build a pile of them dynamically instead:
_alias_factory: Any = TypeAliasType


def test_unwrap_too_many_aliases() -> None:
    """Ensures that we don't hang on endless type aliases."""
    endless: Any = _BodyModel
    for _ in range(_TOO_MANY_ALIASES):
        endless = _alias_factory('endless', endless)

    with pytest.raises(
        UnsolvableAnnotationsError,
        match='too many nested type aliases',
    ):
        unwrap_type_alias(endless)
