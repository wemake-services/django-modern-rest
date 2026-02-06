import json
from http import HTTPStatus
from typing import Any

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from django_modern_rest import Controller, modify
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.http import HttpBasicSyncAuth, basic_auth
from django_modern_rest.serializer import BaseSerializer
from django_modern_rest.settings import Settings
from django_modern_rest.test import DMRRequestFactory


class _HttpBasicAuth(HttpBasicSyncAuth):
    @override
    def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Any | None:
        if username == 'test' and password == 'pass':  # noqa: S105
            return True
        return None


@pytest.fixture(autouse=True)
def _setup_auth(settings: LazySettings, dmr_clean_settings: None) -> None:
    settings.DMR_SETTINGS = {
        Settings.auth: [_HttpBasicAuth()],
    }


def test_sync_basic_auth_success(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that sync controllers work with http basic auth."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            return 'authed'

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.responses.keys() == {
        HTTPStatus.OK,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.NOT_ACCEPTABLE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
    }

    request = dmr_rf.get(
        '/whatever/',
        headers={'Authorization': basic_auth('test', 'pass')},
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


@pytest.mark.parametrize(
    'request_headers',
    [
        {},
        {'Authorization': basic_auth('test', 'wrong')},
        {'Authorization': basic_auth('', 'pass')},
    ],
)
def test_sync_basic_auth_failure(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
) -> None:
    """Ensures that sync controllers work with http basic auth."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.responses.keys() == {
        HTTPStatus.OK,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.NOT_ACCEPTABLE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
    }

    request = dmr_rf.get('/whatever/', headers=request_headers)

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


def test_sync_auth_override_endpoint(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that settings auth can be disabled in endpoint."""

    class _Controller(Controller[PydanticSerializer]):
        @modify(auth=None)
        def get(self) -> str:
            return 'not authed'

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.responses.keys() == {
        HTTPStatus.OK,
        HTTPStatus.NOT_ACCEPTABLE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
    }

    request = dmr_rf.get('/whatever/')

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'not authed'


def test_sync_auth_override_controller(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that settings auth can be disabled in controller."""

    class _Controller(Controller[PydanticSerializer]):
        auth = None

        def get(self) -> str:
            return 'not authed'

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.responses.keys() == {
        HTTPStatus.OK,
        HTTPStatus.NOT_ACCEPTABLE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
    }

    request = dmr_rf.get('/whatever/')

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'not authed'
