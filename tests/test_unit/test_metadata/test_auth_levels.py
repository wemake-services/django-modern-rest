from http import HTTPStatus
from typing import Any

import pytest
from django.conf import LazySettings

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import HeaderJWTSyncAuth
from dmr.settings import Settings


@pytest.mark.parametrize('auth_def', [None, [], ()])
def test_empty_auth_disables_controller(
    *,
    auth_def: Any,
) -> None:
    """Empty `auth` on the endpoint disables all."""

    class _DisabledEndpointController(Controller[PydanticSerializer]):
        auth = [HeaderJWTSyncAuth()]

        @modify(auth=auth_def)
        def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledEndpointController.api_endpoints['GET'].metadata

    assert metadata.auth is None
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses


@pytest.mark.parametrize('auth_def', [None, [], ()])
def test_empty_auth_disables_settings(
    settings: LazySettings,
    *,
    auth_def: Any,
) -> None:
    """Empty `auth` on the endpoint disables all."""
    settings.DMR_SETTTINGS = {Settings.auth: [HeaderJWTSyncAuth()]}

    class _DisabledEndpointController(Controller[PydanticSerializer]):
        auth = auth_def

        def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledEndpointController.api_endpoints['GET'].metadata

    assert metadata.auth is None
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses
