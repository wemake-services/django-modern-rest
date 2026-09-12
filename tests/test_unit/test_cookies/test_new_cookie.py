import dataclasses
import json
from http import HTTPMethod, HTTPStatus
from typing import ClassVar, final

import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import (
    Controller,
    CookieSpec,
    HeaderSpec,
    NewCookie,
    NewHeader,
    ResponseSpec,
    modify,
    validate,
)
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _CookieModifyController(Controller[PydanticSerializer]):
    @modify(
        cookies={
            'session_id': NewCookie(value='123'),
            'Session_Id': NewCookie(value='456', httponly=True),
        },
        headers={'X-Session-Id': NewHeader(value='abc')},
    )
    def get(self) -> list[int]:
        return [1, 2]


def test_add_new_cookies(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that new cookies are added."""
    request = dmr_rf.get('/whatever/')

    response = _CookieModifyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == [1, 2]
    assert response.headers == {
        'Content-Type': 'application/json',
        'X-Session-Id': 'abc',  # header is preserved
    }
    assert response.cookies.output() == snapshot("""\
Set-Cookie: Session_Id=456; HttpOnly; Path=/; SameSite=lax\r
Set-Cookie: session_id=123; Path=/; SameSite=lax\
""")


@final
class _CookieValidateController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            list[int],
            status_code=HTTPStatus.OK,
            cookies={
                'session_id': CookieSpec(max_age=1000),
                'user_id': CookieSpec(httponly=True),
                'optional': CookieSpec(required=False),
            },
            headers={'X-Session-Id': HeaderSpec()},
        ),
    )
    def get(self) -> HttpResponse:
        return self.to_response(
            [1, 2],
            headers={'X-Session-Id': 'abc'},
            cookies={
                'session_id': NewCookie(value='123', max_age=1000),
                'user_id': NewCookie(value='456', httponly=True),
            },
        )

    @validate(
        ResponseSpec(
            list[int],
            status_code=HTTPStatus.CREATED,
            cookies={'optional': CookieSpec(required=False, samesite='strict')},
        ),
    )
    def post(self) -> HttpResponse:
        return self.to_response(
            [1, 2],
            cookies={
                'optional': NewCookie(value='123', samesite='strict'),
            },
        )


@pytest.mark.freeze_time('02-11-2025 10:15:00')
def test_validate_correct_cookies(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that new cookies are validated."""
    request = dmr_rf.get('/whatever/')

    response = _CookieValidateController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == [1, 2]
    assert response.headers == {
        'Content-Type': 'application/json',
        'X-Session-Id': 'abc',  # header is preserved
    }
    assert response.cookies.output() == snapshot("""\
Set-Cookie: session_id=123; expires=Tue, 11 Feb 2025 10:31:40 GMT; \
Max-Age=1000; Path=/; SameSite=lax\r
Set-Cookie: user_id=456; HttpOnly; Path=/; SameSite=lax\
""")


def test_validate_correct_optional(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that new optional cookies are validated."""
    request = dmr_rf.post('/whatever/', data={})

    response = _CookieValidateController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == [1, 2]
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.cookies.output() == snapshot(
        'Set-Cookie: optional=123; Path=/; SameSite=strict',
    )


@final
class _WrongCookieController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            list[int],
            status_code=HTTPStatus.OK,
            cookies={
                'session_id': CookieSpec(max_age=1000),
            },
        ),
    )
    def get(self) -> HttpResponse:
        return self.to_response(
            [1, 2],
            cookies={
                'session_id': NewCookie(value='123'),  # no max-age
            },
        )

    @validate(
        ResponseSpec(
            list[int],
            status_code=HTTPStatus.OK,
            cookies={
                'session_id': CookieSpec(),
            },
        ),
    )
    def post(self) -> HttpResponse:
        return self.to_response(
            [1, 2],
            cookies={},  # no cookie
            status_code=HTTPStatus.OK,
        )

    @validate(
        ResponseSpec(
            list[int],
            status_code=HTTPStatus.OK,
        ),
    )
    def put(self) -> HttpResponse:
        return self.to_response(
            [1, 2],
            cookies={'session_id': NewCookie(value='123')},  # extra cookie
            status_code=HTTPStatus.OK,
        )

    @validate(
        ResponseSpec(
            list[int],
            status_code=HTTPStatus.OK,
            cookies={
                'Session_Id': CookieSpec(),
            },
        ),
    )
    def patch(self) -> HttpResponse:
        return self.to_response(
            [1, 2],
            cookies={
                'session_id': NewCookie(value='123'),  # wrong case
            },
        )

    @validate(
        ResponseSpec(
            list[int],
            status_code=HTTPStatus.OK,
            cookies={
                'session_id': CookieSpec(),
            },
        ),
    )
    def delete(self) -> HttpResponse:
        return self.to_response(
            [1, 2],
            cookies={
                'Session_Id': NewCookie(value='123'),  # wrong case
            },
        )


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
        HTTPMethod.DELETE,
    ],
)
def test_validate_cookies(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that validation for cookies work."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WrongCookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        response.content
    )
    assert json.loads(response.content)['detail']


@final
class _DiscardCookieController(Controller[PydanticSerializer]):
    """Shows how cookies are dropped: empty value and ``max_age=0``."""

    _spec: ClassVar[CookieSpec] = CookieSpec(
        max_age=0,
        httponly=True,
        secure=True,
        samesite='strict',
        path='/api/',
    )

    @validate(
        ResponseSpec(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            cookies={'session_id': _spec},
        ),
    )
    def get(self) -> HttpResponse:
        return self.to_response(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            cookies={'session_id': NewCookie.from_spec(self._spec, value='')},
        )


@pytest.mark.freeze_time('02-11-2025 10:15:00')
def test_discard_cookies(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that a `max_age=0` cookie matches its spec."""
    request = dmr_rf.get('/whatever/')

    response = _DiscardCookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.cookies.output() == snapshot("""\
Set-Cookie: session_id=""; expires=Tue, 11 Feb 2025 10:15:00 GMT; HttpOnly; \
Max-Age=0; Path=/api/; SameSite=strict; Secure\
""")


def test_new_cookie_from_spec() -> None:
    """Ensures that all the spec flags are copied to the new cookie."""
    spec = CookieSpec(
        path='/api/',
        max_age=100,
        domain='example.com',
        secure=True,
        httponly=True,
        samesite='strict',
        description='Only used for the docs.',
        required=False,
        skip_validation=True,
    )

    cookie = NewCookie.from_spec(spec, value='abc')

    assert cookie == NewCookie(
        value='abc',
        path='/api/',
        max_age=100,
        domain='example.com',
        secure=True,
        httponly=True,
        samesite='strict',
    )
    assert cookie.to_spec() == dataclasses.replace(
        spec,
        description=None,
        required=True,
        skip_validation=False,
    )
