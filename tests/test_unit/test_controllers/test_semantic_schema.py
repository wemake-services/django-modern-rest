from http import HTTPStatus

from django.conf import LazySettings
from django.http import HttpResponse

from dmr import Controller, ResponseSpec, modify, validate
from dmr.openapi import OpenAPIContext
from dmr.openapi.generators import SecuritySchemeGenerator
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import HeaderJWTAsyncAuth, HeaderJWTSyncAuth
from dmr.settings import Settings


def test_semantic_schema_settings(
    openapi_context: OpenAPIContext,
    settings: LazySettings,
) -> None:
    """Ensure that semantic schema can be disabled on controller level."""
    settings.DMR_SETTINGS = {Settings.semantic_schema: False}

    class _PerController(Controller[PydanticSerializer]):
        auth = (HeaderJWTSyncAuth(),)

        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerController.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerController,
    )

    assert metadata.semantic_schema is False
    assert metadata.semantic_auth is False
    assert metadata.semantic_responses is False
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses
    assert requirements is None
    assert openapi_context.registries.security_scheme.schemes == {}


def test_semantic_schema_controller(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic schema can be disabled on controller level."""

    class _PerController(Controller[PydanticSerializer]):
        auth = (HeaderJWTSyncAuth(),)
        semantic_schema = False

        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerController.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerController,
    )

    assert metadata.semantic_schema is False
    assert metadata.semantic_auth is False
    assert metadata.semantic_responses is False
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses
    assert requirements is None
    assert openapi_context.registries.security_scheme.schemes == {}


def test_semantic_schema_modify(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be disabled on endpoint level."""

    class _PerEndpoint(Controller[PydanticSerializer]):
        @modify(
            auth=[HeaderJWTSyncAuth()],
            semantic_schema=False,
        )
        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerEndpoint.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerEndpoint,
    )

    assert metadata.semantic_schema is False
    assert metadata.semantic_auth is False
    assert metadata.semantic_responses is False
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses
    assert requirements is None
    assert openapi_context.registries.security_scheme.schemes == {}


def test_semantic_schema_async_validate(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be disabled on endpoint level."""

    class _PerEndpoint(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            auth=[HeaderJWTAsyncAuth()],
            semantic_schema=False,
        )
        async def get(self) -> HttpResponse:
            raise NotImplementedError

    metadata = _PerEndpoint.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerEndpoint,
    )

    assert metadata.semantic_schema is False
    assert metadata.semantic_auth is False
    assert metadata.semantic_responses is False
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses
    assert requirements is None
    assert openapi_context.registries.security_scheme.schemes == {}


def test_semantic_schema_csrf(
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that semantic auth can be disabled on endpoint level."""

    class _PerEndpoint(Controller[PydanticSerializer]):
        csrf_exempt = False

        @modify(
            auth=[HeaderJWTSyncAuth()],
            semantic_schema=False,
        )
        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerEndpoint.api_endpoints['GET'].metadata
    requirements = SecuritySchemeGenerator(openapi_context)(
        metadata,
        _PerEndpoint,
    )

    assert metadata.semantic_schema is False
    assert metadata.semantic_auth is False
    assert metadata.semantic_responses is False
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses
    assert requirements is None
    assert openapi_context.registries.security_scheme.schemes == {}
