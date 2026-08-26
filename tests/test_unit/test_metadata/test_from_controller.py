import json
from collections.abc import Mapping
from http import HTTPStatus
from typing import ClassVar, TypeVar, final

import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import (
    Controller,
    CookieSpec,
    FromController,
    NewHeader,
    ResponseSpec,
    modify,
    validate,
)
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)


class _ReusableCookieController(Controller[_SerializerT]):
    """Reusable base: ``@validate`` runs here, names come from subclasses."""

    access_cookie: ClassVar[str] = 'access_token'

    @classmethod
    def cookie_specs(cls) -> Mapping[str, CookieSpec]:
        """Single source of truth for the schema and the real cookies."""
        return {cls.access_cookie: CookieSpec(httponly=True, secure=True)}

    @validate(
        ResponseSpec(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            cookies=FromController(cookie_specs),
        ),
    )
    def post(self) -> HttpResponse:
        """Cookies are derived from their own specs, so they cannot drift."""
        return self.to_response(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            cookies={
                cookie_key: spec.to_new('token-value')
                for cookie_key, spec in type(self).cookie_specs().items()
            },
        )


@final
class _DefaultCookieController(_ReusableCookieController[PydanticSerializer]):
    """Keeps the inherited cookie name."""


@final
class _CustomCookieController(_ReusableCookieController[PydanticSerializer]):
    """Changes the cookie name with a ``ClassVar``."""

    access_cookie: ClassVar[str] = 'custom_token'


@final
class _OverriddenCookieController(
    _ReusableCookieController[PydanticSerializer],
):
    """Overrides the whole method, not just the ``ClassVar``."""

    @override
    @classmethod
    def cookie_specs(cls) -> Mapping[str, CookieSpec]:
        """Both cookies are described and set."""
        return {
            'first_token': CookieSpec(httponly=True, secure=True),
            'second_token': CookieSpec(httponly=True, secure=True),
        }


def _response_cookies(
    controller_cls: type[Controller[BaseSerializer]],
) -> Mapping[str, CookieSpec]:
    metadata = controller_cls.api_endpoints['POST'].metadata
    cookies = metadata.responses[HTTPStatus.NO_CONTENT].cookies
    assert cookies is not None
    return cookies


def test_classvar_changes_the_spec_per_subclass() -> None:
    """Each concrete controller gets its own resolved cookie names."""
    assert set(_response_cookies(_DefaultCookieController)) == {'access_token'}
    assert set(_response_cookies(_CustomCookieController)) == {'custom_token'}


def test_method_override_changes_the_spec() -> None:
    """We resolve by name, so overriding the method itself works."""
    assert set(_response_cookies(_OverriddenCookieController)) == {
        'first_token',
        'second_token',
    }


def test_resolved_spec_is_a_regular_mapping() -> None:
    """Nothing lazy is left in the finished metadata."""
    cookies = _response_cookies(_DefaultCookieController)

    assert not isinstance(cookies, FromController)
    assert cookies == {
        'access_token': CookieSpec(httponly=True, secure=True),
    }


@pytest.mark.parametrize(
    ('controller_cls', 'cookie_key'),
    [
        (_DefaultCookieController, 'access_token'),
        (_CustomCookieController, 'custom_token'),
    ],
)
def test_lazy_cookies_are_set_and_validated(
    dmr_rf: DMRRequestFactory,
    controller_cls: type[Controller[BaseSerializer]],
    cookie_key: str,
) -> None:
    """Response validation passes, because specs and cookies share a source."""
    request = dmr_rf.post('/whatever/', data={})

    response = controller_cls.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert set(response.cookies) == {cookie_key}


class _ReusableHeaderController(Controller[_SerializerT]):
    """Same trick, but for ``@modify`` and headers."""

    header_name: ClassVar[str] = 'X-Default-Header'

    @classmethod
    def header_specs(cls) -> Mapping[str, NewHeader]:
        """Headers that this controller adds to every response."""
        return {cls.header_name: NewHeader(value='abc')}

    @modify(headers=FromController(header_specs))
    def get(self) -> list[int]:
        """Just some data to render."""
        return [1, 2]


@final
class _CustomHeaderController(_ReusableHeaderController[PydanticSerializer]):
    """Changes the header name with a ``ClassVar``."""

    header_name: ClassVar[str] = 'X-Custom-Header'


def test_lazy_headers_in_modify(dmr_rf: DMRRequestFactory) -> None:
    """``@modify`` resolves lazy headers before it builds the modification."""
    request = dmr_rf.get('/whatever/')

    response = _CustomHeaderController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == [1, 2]
    assert response.headers == {
        'Content-Type': 'application/json',
        'X-Custom-Header': 'abc',
    }


def test_unresolved_mapping_cannot_be_read() -> None:
    """An unresolved mapping fails loudly instead of looking empty."""
    lazy = FromController(
        _ReusableCookieController.__dict__['cookie_specs'],
    )

    with pytest.raises(EndpointMetadataError, match='resolved'):
        len(lazy)  # noqa: WPS421
    with pytest.raises(EndpointMetadataError, match='resolved'):
        lazy['access_token']  # noqa: WPS428
    with pytest.raises(EndpointMetadataError, match='resolved'):
        dict(lazy)


def test_unresolved_mapping_repr() -> None:
    """Error messages must show which method was not resolved."""
    lazy = FromController(
        _ReusableCookieController.__dict__['cookie_specs'],
    )

    assert repr(lazy) == snapshot("FromController('cookie_specs')")
