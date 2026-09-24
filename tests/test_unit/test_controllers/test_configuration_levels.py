import json
from http import HTTPStatus
from typing import Any, Self

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller, ResponseSpec, modify
from dmr.endpoint import Endpoint
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.http import HttpBasicSyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import (
    HttpSpec,
    Settings,
    default_parser,
    default_renderer,
)
from dmr.test import DMRRequestFactory
from dmr.throttling import Rate, SyncThrottle
from dmr.types import EMPTY

pytestmark = pytest.mark.filterwarnings(
    'ignore::dmr.throttling.backends.django_cache.UnsafeCacheBackendWarning',
)


class _SettingsAuth(HttpBasicSyncAuth):
    @override
    def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        return self  # pragma: no cover


class _ControllerAuth(_SettingsAuth):
    """Auth type to be used on the controller level."""


class _EndpointAuth(_SettingsAuth):
    """Auth type to be used on the endpoint level."""


_SETTINGS_AUTH = _SettingsAuth()
_CONTROLLER_AUTH = _ControllerAuth()
_ENDPOINT_AUTH = _EndpointAuth()

_SETTINGS_THROTTLE = SyncThrottle(1, Rate.second)
_CONTROLLER_THROTTLING = (SyncThrottle(2, Rate.minute),)
_SETTINGS_RESPONSE = ResponseSpec(int, status_code=HTTPStatus.PAYMENT_REQUIRED)
_CONTROLLER_RESPONSE = ResponseSpec(str, status_code=HTTPStatus.NOT_FOUND)
_ENDPOINT_RESPONSE = ResponseSpec(bool, status_code=HTTPStatus.CONFLICT)


@pytest.fixture(autouse=True)
def _setup_settings(settings: LazySettings) -> None:
    settings.DMR_SETTINGS = {
        Settings.auth: [_SETTINGS_AUTH],
        Settings.throttling: [_SETTINGS_THROTTLE],
        Settings.exclude_validate_responses: {HTTPStatus.INTERNAL_SERVER_ERROR},
        Settings.no_validate_http_spec: {HttpSpec.empty_request_body},
        Settings.responses: [_SETTINGS_RESPONSE],
    }


def test_controller_overrides_settings() -> None:
    """Ensure that controller values replace settings values."""

    class _Controller(Controller[PydanticSerializer]):
        auth = (_CONTROLLER_AUTH,)
        throttling = _CONTROLLER_THROTTLING
        exclude_validate_responses = frozenset((HTTPStatus.NOT_FOUND,))
        no_validate_http_spec = frozenset((HttpSpec.empty_response_body,))
        responses = (_CONTROLLER_RESPONSE,)
        tags = ('controller',)

        def get(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.auth == [_CONTROLLER_AUTH]
    assert metadata.throttling == list(_CONTROLLER_THROTTLING)
    assert metadata.exclude_validate_responses == {HTTPStatus.NOT_FOUND}
    assert metadata.no_validate_http_spec == {HttpSpec.empty_response_body}
    assert metadata.tags == ['controller']
    assert HTTPStatus.NOT_FOUND in metadata.responses
    assert HTTPStatus.PAYMENT_REQUIRED not in metadata.responses


def test_endpoint_overrides_controller() -> None:
    """Ensure that endpoint values replace controller and settings values."""
    endpoint_throttle = SyncThrottle(3, Rate.hour)

    class _Controller(Controller[PydanticSerializer]):
        auth = (_CONTROLLER_AUTH,)
        throttling = _CONTROLLER_THROTTLING
        exclude_validate_responses = frozenset((HTTPStatus.NOT_FOUND,))
        no_validate_http_spec = frozenset((HttpSpec.empty_response_body,))
        responses = (_CONTROLLER_RESPONSE,)
        tags = ('controller',)

        @modify(
            auth=[_ENDPOINT_AUTH],
            throttling=[endpoint_throttle],
            exclude_validate_responses={HTTPStatus.BAD_GATEWAY},
            no_validate_http_spec={HttpSpec.header_name_syntax},
            extra_responses=[_ENDPOINT_RESPONSE],
            tags=['endpoint'],
        )
        def get(self) -> str:
            raise NotImplementedError

        def post(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.auth == [_ENDPOINT_AUTH]
    assert metadata.throttling == [endpoint_throttle]
    assert metadata.exclude_validate_responses == {HTTPStatus.BAD_GATEWAY}
    assert metadata.no_validate_http_spec == {HttpSpec.header_name_syntax}
    assert metadata.tags == ['endpoint']
    assert HTTPStatus.CONFLICT in metadata.responses
    assert HTTPStatus.NOT_FOUND not in metadata.responses
    assert HTTPStatus.PAYMENT_REQUIRED not in metadata.responses

    # Other endpoints still use the controller values:
    metadata = _Controller.api_endpoints['POST'].metadata
    assert metadata.auth == [_CONTROLLER_AUTH]
    assert metadata.throttling == list(_CONTROLLER_THROTTLING)
    assert metadata.exclude_validate_responses == {HTTPStatus.NOT_FOUND}
    assert metadata.no_validate_http_spec == {HttpSpec.empty_response_body}
    assert metadata.tags == ['controller']
    assert HTTPStatus.NOT_FOUND in metadata.responses
    assert HTTPStatus.CONFLICT not in metadata.responses


def test_explicit_merge() -> None:
    """Ensure that values can still be merged explicitly."""

    class _Controller(Controller[PydanticSerializer]):
        auth = (_CONTROLLER_AUTH, _SETTINGS_AUTH)
        throttling = (*_CONTROLLER_THROTTLING, _SETTINGS_THROTTLE)
        responses = (_CONTROLLER_RESPONSE, _SETTINGS_RESPONSE)

        @modify(
            auth=[_ENDPOINT_AUTH, *auth],
            throttling=list(throttling),
            extra_responses=[_ENDPOINT_RESPONSE, *responses],
        )
        def get(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.auth == [_ENDPOINT_AUTH, _CONTROLLER_AUTH, _SETTINGS_AUTH]
    assert metadata.throttling == [*_CONTROLLER_THROTTLING, _SETTINGS_THROTTLE]
    assert metadata.responses.keys() >= {
        HTTPStatus.CONFLICT,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.PAYMENT_REQUIRED,
    }


@pytest.mark.parametrize('unset', [EMPTY, (), []])
def test_empty_values_are_not_set(
    *,
    unset: Any,
) -> None:
    """Ensure that `EMPTY` and empty values use the next level."""

    class _Controller(Controller[PydanticSerializer]):
        auth = unset
        throttling = unset
        parsers = unset
        renderers = unset
        exclude_validate_responses = unset
        no_validate_http_spec = unset
        responses = unset
        tags = unset

        @modify(  # type: ignore[untyped-decorator]
            auth=unset,
            throttling=unset,
            parsers=unset,
            renderers=unset,
            exclude_validate_responses=unset,
            no_validate_http_spec=unset,
            extra_responses=unset,
            tags=unset,
        )
        def get(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.auth == [_SETTINGS_AUTH]
    assert metadata.throttling == [_SETTINGS_THROTTLE]
    assert metadata.tags is EMPTY
    assert HTTPStatus.PAYMENT_REQUIRED in metadata.responses
    assert metadata.exclude_validate_responses == {
        HTTPStatus.INTERNAL_SERVER_ERROR,
    }
    assert metadata.no_validate_http_spec == {HttpSpec.empty_request_body}
    assert metadata.parsers == {default_parser.content_type: default_parser}
    assert metadata.renderers == {
        default_renderer.content_type: default_renderer,
    }


def test_empty_settings_flags(settings: LazySettings) -> None:
    """Ensure that `EMPTY` boolean settings fall back to defaults."""
    settings.DMR_SETTINGS = {
        Settings.validate_responses: True,
        Settings.semantic_responses: EMPTY,
        Settings.validate_negotiation: EMPTY,
        Settings.validate_events: EMPTY,
    }

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.validate_responses is True
    assert metadata.semantic_responses is True
    assert metadata.validate_negotiation is True
    assert metadata.validate_events is True


def test_none_disables_next_levels() -> None:
    """Ensure that `None` on the controller disables settings values."""

    class _Controller(Controller[PydanticSerializer]):
        auth = None
        throttling = None
        exclude_validate_responses = None
        no_validate_http_spec = None
        responses = None
        tags = None

        def get(self) -> str:
            raise NotImplementedError

        # But, endpoints can still define their own values:
        @modify(
            auth=[_ENDPOINT_AUTH],
            throttling=[_SETTINGS_THROTTLE],
            extra_responses=[_ENDPOINT_RESPONSE],
            tags=['endpoint'],
        )
        def post(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.auth is None
    assert metadata.throttling is None
    assert metadata.exclude_validate_responses == frozenset()
    assert metadata.no_validate_http_spec == frozenset()
    assert metadata.tags is None
    assert HTTPStatus.PAYMENT_REQUIRED not in metadata.responses

    metadata = _Controller.api_endpoints['POST'].metadata
    assert metadata.auth == [_ENDPOINT_AUTH]
    assert metadata.throttling == [_SETTINGS_THROTTLE]
    assert metadata.tags == ['endpoint']
    assert HTTPStatus.CONFLICT in metadata.responses


def test_endpoint_none_disables_controller() -> None:
    """Ensure that `None` on the endpoint disables controller values."""

    class _Controller(Controller[PydanticSerializer]):
        auth = (_CONTROLLER_AUTH,)
        throttling = _CONTROLLER_THROTTLING
        exclude_validate_responses = frozenset((HTTPStatus.NOT_FOUND,))
        responses = (_CONTROLLER_RESPONSE,)
        tags = ('controller',)

        @modify(
            auth=None,
            throttling=None,
            exclude_validate_responses=None,
            extra_responses=None,
            tags=None,
        )
        def get(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.auth is None
    assert metadata.throttling is None
    assert metadata.exclude_validate_responses == frozenset()
    assert metadata.tags is None
    assert HTTPStatus.NOT_FOUND not in metadata.responses


def test_overridden_levels_are_not_validated() -> None:
    """Ensure that only the effective level is validated."""

    class _Controller(Controller[PydanticSerializer]):
        # Wrong for an async endpoint, but it is overridden:
        auth = (_CONTROLLER_AUTH,)

        @modify(auth=None, throttling=None)
        async def get(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.auth is None

    with pytest.raises(EndpointMetadataError, match='AsyncAuth'):

        class _WrongController(Controller[PydanticSerializer]):
            auth = (_CONTROLLER_AUTH,)
            throttling = None

            async def get(self) -> str:
                raise NotImplementedError


def test_override_works_in_runtime(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that overridden settings auth is not used in runtime."""

    class _Controller(Controller[PydanticSerializer]):
        auth = None
        throttling = None

        def get(self) -> str:
            return 'not authed'

    request = dmr_rf.get('/whatever/')
    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'not authed'
