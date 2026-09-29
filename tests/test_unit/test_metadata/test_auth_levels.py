from collections.abc import Sequence
from http import HTTPStatus
from types import MappingProxyType
from typing import Any, Self

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from django.urls import path
from typing_extensions import override

from dmr import Controller, ResponseSpec, modify, validate
from dmr.endpoint import Endpoint
from dmr.exceptions import EndpointMetadataError
from dmr.metadata import EndpointMetadata
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.security import SyncAuth
from dmr.security.jwt import HeaderJWTSyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import Settings


@pytest.mark.parametrize('auth_def', [None, [], ()])
def test_endpoint_empty_auth_disables_controller(
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


@pytest.mark.parametrize('auth_def', [None, [], ()])
def test_endpoint_empty_auth_disables_settings(
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
