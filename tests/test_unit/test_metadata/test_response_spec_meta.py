import json
from collections.abc import Mapping
from http import HTTPMethod, HTTPStatus
from typing import Annotated, Any, Final, TypeAlias

import pydantic
import pytest
from django.http import HttpResponse
from django.urls import path
from inline_snapshot import snapshot
from syrupy.assertion import SnapshotAssertion
from typing_extensions import TypeAliasType, override

from dmr import Body, Controller, Query, ResponseSpec, modify, validate
from dmr.cookies import CookieSpec, NewCookie
from dmr.errors import ErrorModel
from dmr.headers import HeaderSpec, NewHeader
from dmr.metadata import ResponseSpecMetadata
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.routing import Router
from dmr.test import DMRRequestFactory

_HEADER_VALUE: Final = 'header_whatever'
_COOKIE_VALUE: Final = 'cookie_whatever'


class _BodyModel(pydantic.BaseModel):
    number: int


class _HeaderAndCookieController(Controller[PydanticSerializer]):
    error_model = Annotated[
        ErrorModel,
        ResponseSpecMetadata(
            headers={'X-Reply': HeaderSpec()},
            cookies={'x-test': CookieSpec()},
        ),
    ]

    @modify(
        headers={
            'X-Reply': NewHeader(value=_HEADER_VALUE),
            'X-Success': NewHeader(value='true'),
        },
        cookies={'x-test': NewCookie(value=_COOKIE_VALUE)},
    )
    def patch(self, parsed_body: Body[_BodyModel]) -> _BodyModel:
        return parsed_body

    @validate(
        ResponseSpec(
            _BodyModel,
            status_code=HTTPStatus.OK,
            headers={
                'X-Reply': HeaderSpec(),
                'X-Success': HeaderSpec(),
            },
            cookies={'x-test': CookieSpec()},
        ),
    )
    def put(self, parsed_body: Body[_BodyModel]) -> HttpResponse:
        return self.to_response(parsed_body, headers={'X-Success': 'true'})

    @override
    def to_response(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus | None = None,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        renderer: Renderer | None = None,
    ) -> HttpResponse:
        headers = dict(headers or {})
        headers.setdefault('X-Reply', _HEADER_VALUE)

        cookies = dict(cookies or {})
        cookies.setdefault(
            'x-test',
            NewCookie(value=_COOKIE_VALUE),
        )
        return super().to_response(
            raw_data,
            status_code=status_code,
            headers=headers,
            cookies=cookies,
            renderer=renderer,
        )


@pytest.mark.parametrize('method', [HTTPMethod.PATCH, HTTPMethod.PUT])
def test_header_and_cookie_success(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that correct responses provide headers and cookies."""
    request_data = {'number': 1}
    request = dmr_rf.generic(
        str(method),
        '/any/',
        data=json.dumps(request_data),
    )

    response = _HeaderAndCookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'Content-Type': 'application/json',
        'X-Reply': _HEADER_VALUE,
        'X-Success': 'true',
    }
    assert (
        response.cookies.output()
        == f'Set-Cookie: x-test={_COOKIE_VALUE}; Path=/; SameSite=lax'
    )
    assert json.loads(response.content) == request_data


@pytest.mark.parametrize('method', [HTTPMethod.PATCH, HTTPMethod.PUT])
def test_header_and_cookie_error(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that error responses provide headers and cookies."""
    request = dmr_rf.generic(
        str(method),
        '/any/',
        data=json.dumps({'number': 'wrong'}),
    )

    response = _HeaderAndCookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {
        'Content-Type': 'application/json',
        'X-Reply': _HEADER_VALUE,
    }
    assert (
        response.cookies.output()
        == f'Set-Cookie: x-test={_COOKIE_VALUE}; Path=/; SameSite=lax'
    )
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Input should be a valid integer, '
                    'unable to parse string as an integer'
                ),
                'loc': ['parsed_body', 'number'],
                'type': 'value_error',
            },
        ],
    })


def test_error_model_with_metadata_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for error models with annotations."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path(
                            '/header-and-cookie',
                            _HeaderAndCookieController.as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


_UNION_HEADER: Final = 'X-Union'
_UNION_COOKIE: Final = 'union-cookie'
_OTHER_HEADER: Final = 'X-Other'

_UNION_METADATA: Final = ResponseSpecMetadata(
    headers={_UNION_HEADER: HeaderSpec()},
    cookies={_UNION_COOKIE: CookieSpec()},
)

# Only `_BodyModel` responses carry the header and the cookie,
# a plain `str` response does not:
_AnnotatedMember: TypeAlias = Annotated[_BodyModel, _UNION_METADATA]
# Here the whole union carries them, every response has them:
_AnnotatedUnion: TypeAlias = Annotated[_BodyModel | str, _UNION_METADATA]
# Both members carry the very same header:
_AnnotatedString: TypeAlias = Annotated[
    str,
    ResponseSpecMetadata(headers={_UNION_HEADER: HeaderSpec()}),
]

_LazyAnnotatedMember = TypeAliasType('_LazyAnnotatedMember', _AnnotatedMember)


class _UnionMetadataController(Controller[PydanticSerializer]):
    def get(self) -> _AnnotatedMember | str:
        raise NotImplementedError

    def post(self) -> _AnnotatedUnion:
        raise NotImplementedError

    def put(self) -> _AnnotatedMember | _AnnotatedString:
        raise NotImplementedError

    def patch(self) -> _LazyAnnotatedMember | None:
        raise NotImplementedError


@pytest.mark.parametrize(
    ('method', 'status_code', 'required'),
    [
        # One member out of two declares them, so they can be missing:
        (HTTPMethod.GET, HTTPStatus.OK, False),
        # The whole union declares them, so they are always there:
        (HTTPMethod.POST, HTTPStatus.CREATED, True),
        # Both members declare the header, so it is always there:
        (HTTPMethod.PUT, HTTPStatus.OK, True),
        # Same as `get`, but behind a type alias:
        (HTTPMethod.PATCH, HTTPStatus.OK, False),
    ],
)
def test_union_response_spec_metadata(
    *,
    method: HTTPMethod,
    status_code: HTTPStatus,
    required: bool,
) -> None:
    """Ensure that union members and type aliases provide their metadata."""
    endpoint = _UnionMetadataController.api_endpoints[str(method)]
    response_spec = endpoint.metadata.responses[status_code]

    assert response_spec.headers == {
        _UNION_HEADER: HeaderSpec(required=required),
    }


def test_union_response_spec_cookies() -> None:
    """Ensure that cookies of union members are merged just like headers."""
    endpoint = _UnionMetadataController.api_endpoints['GET']
    response_spec = endpoint.metadata.responses[HTTPStatus.OK]

    assert response_spec.cookies == {
        _UNION_COOKIE: CookieSpec(required=False),
    }


def test_merge_keeps_specs_of_both_members() -> None:
    """Ensure that different specs of union members are all kept."""
    merged = ResponseSpecMetadata.merge(
        ResponseSpecMetadata(headers={_UNION_HEADER: HeaderSpec()}),
        ResponseSpecMetadata(headers={_OTHER_HEADER: HeaderSpec()}),
    )

    assert merged is not None
    assert merged.headers == {
        _UNION_HEADER: HeaderSpec(required=False),
        _OTHER_HEADER: HeaderSpec(required=False),
    }
    assert merged.cookies == {}


def test_merge_of_empty_metadata() -> None:
    """Ensure that members without metadata merge into nothing."""
    assert ResponseSpecMetadata.merge(None, None) is None


class _UnionQuery(pydantic.BaseModel):
    identified: bool = False


class _OptionalUnionHeaderController(Controller[PydanticSerializer]):
    @validate(ResponseSpec(_AnnotatedMember | str, status_code=HTTPStatus.OK))
    def get(self, parsed_query: Query[_UnionQuery]) -> HttpResponse:
        if parsed_query.identified:
            # The annotated member, it does provide the header and the cookie:
            return self.to_response(
                _BodyModel(number=1),
                headers={_UNION_HEADER: _HEADER_VALUE},
                cookies={_UNION_COOKIE: NewCookie(value=_COOKIE_VALUE)},
            )
        # The plain `str` member, it provides neither:
        return self.to_response('a string without the header')


def test_union_member_with_header(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that the annotated union member may send the header."""
    request = dmr_rf.get('/whatever/?identified=true')

    response = _OptionalUnionHeaderController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'Content-Type': 'application/json',
        _UNION_HEADER: _HEADER_VALUE,
    }
    assert (
        response.cookies.output()
        == f'Set-Cookie: {_UNION_COOKIE}={_COOKIE_VALUE}; Path=/; SameSite=lax'
    )
    assert json.loads(response.content) == {'number': 1}


def test_union_member_without_header(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that a member without metadata may skip the header."""
    request = dmr_rf.get('/whatever/?identified=false')

    response = _OptionalUnionHeaderController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert not response.cookies
    assert json.loads(response.content) == 'a string without the header'


class _RequiredUnionHeaderController(Controller[PydanticSerializer]):
    @validate(ResponseSpec(_AnnotatedUnion, status_code=HTTPStatus.OK))
    def get(self) -> HttpResponse:
        return self.to_response('a string without the header')


def test_whole_union_headers_are_required(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that metadata of the whole union is required everywhere."""
    request = dmr_rf.get('/whatever/')

    response = _RequiredUnionHeaderController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': "Response has missing required {'x-union'} headers",
                'type': 'value_error',
            },
        ],
    })
