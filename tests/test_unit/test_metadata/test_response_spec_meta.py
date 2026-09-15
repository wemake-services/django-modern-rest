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

from dmr import Body, Controller, ResponseSpec, modify, validate
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

_AnnotatedBody: TypeAlias = Annotated[
    _BodyModel,
    ResponseSpecMetadata(
        headers={_UNION_HEADER: HeaderSpec()},
        cookies={_UNION_COOKIE: CookieSpec()},
    ),
]
_AnnotatedString: TypeAlias = Annotated[
    str,
    ResponseSpecMetadata(headers={_OTHER_HEADER: HeaderSpec()}),
]
_LazyAnnotatedBody = TypeAliasType('_LazyAnnotatedBody', _AnnotatedBody)


class _UnionMetadataController(Controller[PydanticSerializer]):
    def get(self) -> _AnnotatedBody | str:
        raise NotImplementedError

    def post(self) -> _AnnotatedBody | _AnnotatedString:
        raise NotImplementedError

    def put(self) -> _LazyAnnotatedBody | None:
        raise NotImplementedError

    @validate(ResponseSpec(_LazyAnnotatedBody, status_code=HTTPStatus.OK))
    def patch(self) -> HttpResponse:
        raise NotImplementedError


@pytest.mark.parametrize(
    ('method', 'status_code', 'expected_headers'),
    [
        (HTTPMethod.GET, HTTPStatus.OK, [_UNION_HEADER]),
        (
            HTTPMethod.POST,
            HTTPStatus.CREATED,
            [_UNION_HEADER, _OTHER_HEADER],
        ),
        (HTTPMethod.PUT, HTTPStatus.OK, [_UNION_HEADER]),
        (HTTPMethod.PATCH, HTTPStatus.OK, [_UNION_HEADER]),
    ],
)
def test_union_response_spec_metadata(
    *,
    method: HTTPMethod,
    status_code: HTTPStatus,
    expected_headers: list[str],
) -> None:
    """Ensure that metadata is found in union members and type aliases."""
    endpoint = _UnionMetadataController.api_endpoints[str(method)]
    response_spec = endpoint.metadata.responses[status_code]

    assert response_spec.headers is not None
    assert sorted(response_spec.headers) == sorted(expected_headers)
    assert response_spec.cookies == {_UNION_COOKIE: CookieSpec()}


class _UnionMissingHeaderController(Controller[PydanticSerializer]):
    @validate(ResponseSpec(_AnnotatedBody | str, status_code=HTTPStatus.OK))
    def get(self) -> HttpResponse:
        return self.to_response('no headers at all')


def test_union_metadata_headers_are_validated(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that headers from union members are required in responses."""
    request = dmr_rf.get('/whatever/')

    response = _UnionMissingHeaderController.as_view()(request)

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
