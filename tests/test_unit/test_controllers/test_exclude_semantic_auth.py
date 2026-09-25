from http import HTTPStatus
from typing import Self

from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import Controller, ResponseSpec, modify, validate
from dmr.endpoint import Endpoint
from dmr.metadata import EndpointMetadata
from dmr.openapi import OpenAPIContext
from dmr.openapi.generators import SecuritySchemeGenerator
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import SyncAuth
from dmr.security.jwt import HeaderJWTAsyncAuth, HeaderJWTSyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import Settings


class _CustomSyncAuth(SyncAuth):
    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self | None:
        raise NotImplementedError

    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type[Controller[BaseSerializer]],
    ) -> list[SecurityRequirement]:
        return [{'auth1': [], 'auth2': []}]

    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type[Controller[BaseSerializer]],
    ) -> dict[str, SecurityScheme | Reference]:
        return {
            'auth1': SecurityScheme(type='apiKey'),
            'auth2': SecurityScheme(type='http'),
        }

    @property
    @override
    def www_authenticate_challenge(self) -> str | None:
        """Does nothing."""


def test_exclude_semantic_auth_settings(
    openapi_context: OpenAPIContext,
    settings: LazySettings,
) -> None:
    """Ensure that semantic auth can be excluded on settings level."""
    settings.DMR_SETTINGS = {
        Settings.exclude_semantic_auth: frozenset(('auth1',)),
    }

    class _PerSettings(Controller[PydanticSerializer]):
        auth = (HeaderJWTSyncAuth(), _CustomSyncAuth())

        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerSettings.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerSettings,
    )

    assert metadata.exclude_semantic_auth == frozenset(('auth1',))
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert requirements == snapshot([{'jwt': []}, {'auth2': []}])
    assert openapi_context.registries.security_scheme.schemes == snapshot({
        'auth2': SecurityScheme(type='http'),
        'jwt': SecurityScheme(
            type='http',
            description='JWT token auth',
            scheme='Bearer',
            bearer_format='JWT',
        ),
    })


def test_exclude_semantic_auth_controller(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be excluded on controller level."""

    class _PerController(Controller[PydanticSerializer]):
        auth = (HeaderJWTSyncAuth(), _CustomSyncAuth())
        exclude_semantic_auth = frozenset(('auth1',))

        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerController.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerController,
    )

    assert metadata.exclude_semantic_auth == frozenset(('auth1',))
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert requirements == snapshot([{'jwt': []}, {'auth2': []}])
    assert openapi_context.registries.security_scheme.schemes == snapshot({
        'auth2': SecurityScheme(type='http'),
        'jwt': SecurityScheme(
            type='http',
            description='JWT token auth',
            scheme='Bearer',
            bearer_format='JWT',
        ),
    })


def test_exclude_semantic_auth_modify(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be excluded on modify level."""

    class _PerController(Controller[PydanticSerializer]):
        auth = (HeaderJWTAsyncAuth(),)

        @modify(exclude_semantic_auth=frozenset(('jwt',)))
        async def get(self) -> str:
            raise NotImplementedError

    metadata = _PerController.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerController,
    )

    assert metadata.exclude_semantic_auth == frozenset(('jwt',))
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert requirements is None
    assert openapi_context.registries.security_scheme.schemes == {}


def test_exclude_semantic_auth_validate(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be excluded on validate level."""

    class _PerController(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            auth=(HeaderJWTSyncAuth(), _CustomSyncAuth()),
            exclude_semantic_auth=frozenset(('auth1',)),
        )
        def get(self) -> HttpResponse:
            raise NotImplementedError

    metadata = _PerController.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerController,
    )

    assert metadata.exclude_semantic_auth == frozenset(('auth1',))
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert requirements == snapshot([{'jwt': []}, {'auth2': []}])
    assert openapi_context.registries.security_scheme.schemes == snapshot({
        'auth2': SecurityScheme(type='http'),
        'jwt': SecurityScheme(
            type='http',
            description='JWT token auth',
            scheme='Bearer',
            bearer_format='JWT',
        ),
    })


def test_exclude_semantic_auth_csrf(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be disabled on endpoint level."""

    class _PerEndpoint(Controller[PydanticSerializer]):
        csrf_exempt = False

        @modify(
            auth=[HeaderJWTSyncAuth()],
            exclude_semantic_auth={'csrf'},
        )
        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerEndpoint.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerEndpoint,
    )

    assert metadata.semantic_schema is True
    assert metadata.semantic_auth is True
    assert metadata.semantic_responses is True
    assert metadata.exclude_semantic_auth == frozenset(('csrf',))
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert requirements == snapshot([{'jwt': []}])
    assert openapi_context.registries.security_scheme.schemes.keys() == {'jwt'}


def test_disable_semantic_auth_settings(
    openapi_context: OpenAPIContext,
    settings: LazySettings,
) -> None:
    """Ensure that semantic auth can be disabled on settings level."""
    settings.DMR_SETTINGS = {Settings.semantic_auth: False}

    class _PerSettings(Controller[PydanticSerializer]):
        auth = (HeaderJWTSyncAuth(), _CustomSyncAuth())

        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerSettings.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerSettings,
    )

    assert metadata.semantic_schema is True
    assert metadata.semantic_responses is True
    assert metadata.semantic_auth is False
    assert requirements is None
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert openapi_context.registries.security_scheme.schemes == {}


def test_disable_semantic_auth_controller(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be disabled on controller level."""

    class _PerController(Controller[PydanticSerializer]):
        auth = (HeaderJWTSyncAuth(), _CustomSyncAuth())
        semantic_auth = False

        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerController.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerController,
    )

    assert metadata.semantic_schema is True
    assert metadata.semantic_responses is True
    assert metadata.semantic_auth is False
    assert requirements is None
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert openapi_context.registries.security_scheme.schemes == {}


def test_disable_semantic_auth_modify(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be disabled on endpoint level."""

    class _PerEndpoint(Controller[PydanticSerializer]):
        @modify(
            auth=(HeaderJWTSyncAuth(), _CustomSyncAuth()),
            semantic_auth=False,
        )
        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerEndpoint.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerEndpoint,
    )

    assert metadata.semantic_schema is True
    assert metadata.semantic_responses is True
    assert metadata.semantic_auth is False
    assert requirements is None
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert openapi_context.registries.security_scheme.schemes == {}


def test_disable_semantic_auth_async_validate(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be disabled on endpoint level."""

    class _PerEndpoint(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            auth=[HeaderJWTAsyncAuth()],
            semantic_auth=False,
        )
        async def get(self) -> HttpResponse:
            raise NotImplementedError

    metadata = _PerEndpoint.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerEndpoint,
    )

    assert metadata.semantic_schema is True
    assert metadata.semantic_responses is True
    assert metadata.semantic_auth is False
    assert requirements is None
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert openapi_context.registries.security_scheme.schemes == {}


def test_semantic_auth_csrf(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be disabled on endpoint level."""

    class _PerEndpoint(Controller[PydanticSerializer]):
        csrf_exempt = False

        @modify(
            auth=[HeaderJWTSyncAuth()],
            semantic_auth=False,
        )
        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerEndpoint.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerEndpoint,
    )

    assert metadata.semantic_schema is True
    assert metadata.semantic_auth is False
    assert metadata.semantic_responses is True
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
    assert requirements is None
    assert openapi_context.registries.security_scheme.schemes == {}
