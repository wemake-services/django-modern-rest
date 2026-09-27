from http import HTTPStatus
from typing import Any

import pytest
from django.conf import LazySettings, settings

from dmr.controller import Controller
from dmr.openapi.objects import SecurityScheme
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AsyncAuth, SyncAuth
from dmr.security.csrf import CSRF_SCHEME_NAME
from dmr.security.token import (
    CookieTokenAsyncAuth,
    CookieTokenSyncAuth,
    HeaderTokenAsyncAuth,
    HeaderTokenSyncAuth,
)


def _make_controller(
    instance: SyncAuth | AsyncAuth,
) -> type[Controller[PydanticSerializer]]:
    func_def = 'async def' if isinstance(instance, AsyncAuth) else 'def'

    ns: dict[str, Any] = {'instance': instance}
    exec(  # noqa: S102, WPS421
        f"""if True:
    from dmr import Controller
    from dmr.plugins.pydantic import PydanticSerializer

    class _Controller(Controller[PydanticSerializer]):
        auth = (instance,)

        {func_def} get(self) -> str:
            raise NotImplementedError

        {func_def} post(self) -> str:
            raise NotImplementedError
    """,
        ns,
    )
    return ns['_Controller']  # type: ignore[no-any-return]


@pytest.mark.parametrize('typ', [HeaderTokenSyncAuth, HeaderTokenAsyncAuth])
@pytest.mark.parametrize('header_name', ['X-API-Token', 'custom'])
@pytest.mark.parametrize('security_scheme_name', ['token', 'customName'])
@pytest.mark.parametrize('prefix', ['', 'Bearer '])
def test_custom_header_schema(
    *,
    typ: type[HeaderTokenSyncAuth] | type[HeaderTokenAsyncAuth],
    header_name: str,
    security_scheme_name: str,
    prefix: str,
) -> None:
    """Ensures that a custom header is reflected in the schema."""
    instance = typ(
        header_name=header_name,
        security_scheme_name=security_scheme_name,
        prefix=prefix,  # it does not matter
    )

    controller = _make_controller(instance)
    metadata = controller.api_endpoints['GET'].metadata

    assert HTTPStatus.FORBIDDEN not in metadata.responses
    assert instance.security_schemes(metadata, controller) == {
        security_scheme_name: SecurityScheme(
            type='apiKey',
            name=header_name,
            security_scheme_in='header',
            description='Opaque token authentication',
        ),
    }
    assert instance.security_requirements(metadata, controller) == [
        {security_scheme_name: []},
    ]
    assert instance.www_authenticate_challenge is None


@pytest.mark.parametrize('typ', [HeaderTokenSyncAuth, HeaderTokenAsyncAuth])
@pytest.mark.parametrize('security_scheme_name', ['token', 'customName'])
@pytest.mark.parametrize('prefix', ['', 'Bearer '])
def test_header_schema_for_authorization(
    *,
    typ: type[HeaderTokenSyncAuth] | type[HeaderTokenAsyncAuth],
    security_scheme_name: str,
    prefix: str,
) -> None:
    """Ensures that a custom header is reflected in the schema."""
    instance = typ(
        header_name='Authorization',
        security_scheme_name=security_scheme_name,
        prefix=prefix,  # it does not matter
    )

    controller = _make_controller(instance)
    metadata = controller.api_endpoints['GET'].metadata

    assert HTTPStatus.FORBIDDEN not in metadata.responses
    if prefix:
        assert instance.www_authenticate_challenge == 'Bearer'
    else:
        assert instance.www_authenticate_challenge is None
    assert instance.security_schemes(metadata, controller) == {
        security_scheme_name: SecurityScheme(
            type='http',
            scheme='bearer',
            description='Opaque token authentication',
        ),
    }
    assert instance.security_requirements(metadata, controller) == [
        {security_scheme_name: []},
    ]

    unsafe_metadata = controller.api_endpoints['POST'].metadata
    assert HTTPStatus.FORBIDDEN not in unsafe_metadata.responses
    assert instance.security_schemes(
        unsafe_metadata,
        controller,
    ) == instance.security_schemes(metadata, controller)
    assert instance.security_requirements(
        unsafe_metadata,
        controller,
    ) == instance.security_requirements(metadata, controller)


@pytest.mark.parametrize('typ', [CookieTokenSyncAuth, CookieTokenAsyncAuth])
@pytest.mark.parametrize('cookie_name', ['token', 'custom'])
@pytest.mark.parametrize('security_scheme_name', ['token', 'customName'])
@pytest.mark.parametrize('csrf_scheme_name', [CSRF_SCHEME_NAME, 'custom_csrf'])
def test_cookie_token_schema(
    *,
    typ: type[CookieTokenSyncAuth] | type[CookieTokenAsyncAuth],
    cookie_name: str,
    security_scheme_name: str,
    csrf_scheme_name: str,
) -> None:
    """Ensures CookieToken auth emits an apiKey cookie security scheme."""
    instance = typ(
        cookie_name=cookie_name,
        security_scheme_name=security_scheme_name,
        csrf_scheme_name=csrf_scheme_name,
    )

    controller = _make_controller(instance)
    metadata = controller.api_endpoints['GET'].metadata

    assert HTTPStatus.FORBIDDEN not in metadata.responses
    assert instance.www_authenticate_challenge is None
    assert instance.security_schemes(metadata, controller) == {
        security_scheme_name: SecurityScheme(
            type='apiKey',
            name=cookie_name,
            security_scheme_in='cookie',
            description='Opaque token authentication via cookie',
        ),
        csrf_scheme_name: SecurityScheme(
            type='apiKey',
            name=settings.CSRF_COOKIE_NAME,
            security_scheme_in='cookie',
            description='CSRF protection',
        ),
    }
    assert instance.security_requirements(metadata, controller) == [
        {security_scheme_name: []},
    ]

    unsafe_metadata = controller.api_endpoints['POST'].metadata
    assert HTTPStatus.FORBIDDEN in unsafe_metadata.responses
    assert instance.security_schemes(
        unsafe_metadata,
        controller,
    ) == instance.security_schemes(metadata, controller)
    assert instance.security_requirements(unsafe_metadata, controller) == [
        {security_scheme_name: [], csrf_scheme_name: []},
    ]


@pytest.mark.parametrize('typ', [CookieTokenSyncAuth, CookieTokenAsyncAuth])
def test_cookie_token_schema_csrf_session(
    settings: LazySettings,
    *,
    typ: type[CookieTokenSyncAuth] | type[CookieTokenAsyncAuth],
) -> None:
    """Ensures CookieToken auth emits a CSRF header scheme with sessions."""
    settings.CSRF_USE_SESSIONS = True
    instance = typ()
    controller = _make_controller(instance)
    metadata = controller.api_endpoints['GET'].metadata

    assert HTTPStatus.FORBIDDEN not in metadata.responses
    assert instance.www_authenticate_challenge is None
    assert instance.security_schemes(metadata, controller) == {
        'token': SecurityScheme(
            type='apiKey',
            name='token',
            security_scheme_in='cookie',
            description='Opaque token authentication via cookie',
        ),
        'csrf': SecurityScheme(
            type='apiKey',
            name='X-Csrftoken',
            security_scheme_in='header',
            description='CSRF protection, the secret is stored in the session',
        ),
    }
    assert instance.security_requirements(metadata, controller) == [
        {'token': []},
    ]

    unsafe_metadata = controller.api_endpoints['POST'].metadata
    assert HTTPStatus.FORBIDDEN in unsafe_metadata.responses
    assert instance.security_requirements(unsafe_metadata, controller) == [
        {'token': [], 'csrf': []},
    ]
