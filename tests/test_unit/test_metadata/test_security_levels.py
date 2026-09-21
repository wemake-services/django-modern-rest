import re
from collections.abc import Sequence
from http import HTTPStatus
from types import MappingProxyType
from typing import Self, cast

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from django.urls import path
from typing_extensions import override

from dmr import Controller, ResponseSpec, modify, validate
from dmr.endpoint import Endpoint
from dmr.exceptions import EndpointMetadataError
from dmr.metadata import EndpointMetadata
from dmr.openapi import build_schema
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.security import SyncAuth
from dmr.security.jwt import HeaderJWTSyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import Settings


class _SchemaOnlyAuth(SyncAuth):
    """Auth that only knows its schemes during the schema generation."""

    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self | None:
        raise NotImplementedError

    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type[Controller[BaseSerializer]],
    ) -> dict[str, SecurityScheme | Reference]:
        raise NotImplementedError

    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type[Controller[BaseSerializer]],
    ) -> list[SecurityRequirement]:
        raise NotImplementedError

    @property
    @override
    def www_authenticate_challenge(self) -> str | None:
        """This auth has no challenge, so this returns ``None``."""


class _TwoSchemesAuth(_SchemaOnlyAuth):
    """Auth that registers a scheme it does not use in its requirement."""

    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type[Controller[BaseSerializer]],
    ) -> dict[str, SecurityScheme | Reference]:
        return {
            'main': SecurityScheme(type='http', scheme='bearer'),
            'extra': SecurityScheme(type='http', scheme='basic'),
        }

    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type[Controller[BaseSerializer]],
    ) -> list[SecurityRequirement]:
        return [{'main': []}]


class _RawController(Controller[PydanticSerializer]):
    """Controller with an endpoint without any decorators."""

    security = [{'gateway': []}]

    def get(self) -> str:
        raise NotImplementedError


@pytest.fixture
def _settings_security(settings: LazySettings) -> None:
    settings.DMR_SETTINGS = {Settings.security: [{'proxy': []}]}


@pytest.fixture
def _settings_jwt_security(settings: LazySettings) -> None:
    settings.DMR_SETTINGS = {Settings.security: [{'jwt': []}]}


def test_endpoint_security() -> None:
    """Endpoint level `security` is saved to the metadata."""

    class _EndpointController(Controller[PydanticSerializer]):
        @modify(security=[{'gateway': []}])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _EndpointController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}]


def test_endpoint_security_with_validate() -> None:
    """`@validate` also saves `security` to the metadata."""

    class _ValidateController(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(return_type=str, status_code=HTTPStatus.OK),
            security=[{'gateway': []}],
        )
        def get(self) -> HttpResponse:
            raise NotImplementedError

    metadata = _ValidateController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}]


def test_async_endpoint_security() -> None:
    """Async endpoints save `security` just like sync ones."""

    class _AsyncController(Controller[PydanticSerializer]):
        @modify(security=[{'gateway': []}])
        async def get(self) -> str:
            raise NotImplementedError

    metadata = _AsyncController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}]


def test_controller_security() -> None:
    """Controller level `security` is applied to all its endpoints."""

    class _ControllerLevelController(Controller[PydanticSerializer]):
        security = [{'gateway': []}]

        @modify()
        def get(self) -> str:
            raise NotImplementedError

    metadata = _ControllerLevelController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}]


def test_raw_endpoint_security() -> None:
    """Endpoints without decorators also get the inherited `security`."""
    metadata = _RawController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}]


@pytest.mark.usefixtures('_settings_security')
def test_raw_endpoint_settings_security() -> None:
    """Endpoints without decorators also merge the settings level."""

    class _RawSettingsController(Controller[PydanticSerializer]):
        security = [{'gateway': []}]

        def get(self) -> str:
            raise NotImplementedError

    assert _RawSettingsController.api_endpoints['GET'].metadata.security == [
        {'gateway': []},
        {'proxy': []},
    ]


@pytest.mark.usefixtures('_settings_security')
def test_settings_security() -> None:
    """Settings level `security` is applied to all endpoints."""

    class _SettingsController(Controller[PydanticSerializer]):
        @modify()
        def get(self) -> str:
            raise NotImplementedError

    metadata = _SettingsController.api_endpoints['GET'].metadata

    assert metadata.security == [{'proxy': []}]


@pytest.mark.usefixtures('_settings_security')
def test_all_security_levels_are_merged() -> None:
    """All levels are merged: endpoint, controller, and settings."""

    class _MergedController(Controller[PydanticSerializer]):
        security = [{'controller': []}]

        @modify(security=[{'endpoint': []}])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _MergedController.api_endpoints['GET'].metadata

    assert metadata.security == [
        {'endpoint': []},
        {'controller': []},
        {'proxy': []},
    ]


def test_duplicate_security_is_merged_once() -> None:
    """The same requirement from several levels is only added once."""

    class _DuplicateController(Controller[PydanticSerializer]):
        security = [{'gateway': []}]

        @modify(security=[{'gateway': []}])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _DuplicateController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}]


@pytest.mark.usefixtures('_settings_security')
def test_endpoint_security_none_disables_security() -> None:
    """`security=None` on the endpoint disables all inherited requirements."""

    class _DisabledEndpointController(Controller[PydanticSerializer]):
        security = [{'gateway': []}]

        @modify(security=None)
        def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledEndpointController.api_endpoints['GET'].metadata

    assert metadata.security is None


@pytest.mark.usefixtures('_settings_security')
def test_controller_security_none_disables() -> None:
    """`security = None` on the controller disables inherited requirements."""

    class _DisabledController(Controller[PydanticSerializer]):
        security = None

        @modify()
        def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledController.api_endpoints['GET'].metadata

    assert metadata.security is None


@pytest.mark.usefixtures('_settings_security')
def test_controller_none_wins_over_endpoint() -> None:
    """Controller `None` also drops the endpoint level requirements."""

    class _DisabledEverythingController(Controller[PydanticSerializer]):
        security = None

        @modify(security=[{'gateway': []}])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledEverythingController.api_endpoints['GET'].metadata

    assert metadata.security is None


@pytest.mark.usefixtures('_settings_security')
def test_settings_duplicate_security_once() -> None:
    """The settings level is deduplicated together with the other ones."""

    class _SettingsDuplicateController(Controller[PydanticSerializer]):
        @modify(security=[{'proxy': []}])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _SettingsDuplicateController.api_endpoints['GET'].metadata

    assert metadata.security == [{'proxy': []}]


def test_empty_security_adds_nothing() -> None:
    """Empty `security` means that this level adds no requirements."""

    class _EmptyController(Controller[PydanticSerializer]):
        @modify(security=[])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _EmptyController.api_endpoints['GET'].metadata

    assert metadata.security is None


def test_security_intersection_with_auth() -> None:
    """Schemes from `auth` cannot be redefined by `security`."""

    class _IntersectionController(Controller[PydanticSerializer]):
        @modify(auth=[HeaderJWTSyncAuth()], security=[{'jwt': []}])
        def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match=r"Security schemes \['jwt'\] are already generated",
    ):
        build_schema(
            Router('api/', [path('user/', _IntersectionController.as_view())]),
        ).convert()


def test_security_reuses_registered_scheme() -> None:
    """Schemes that `auth` registers cannot be reused either."""

    class _RegisteredOnlyController(Controller[PydanticSerializer]):
        @modify(
            auth=[_TwoSchemesAuth()],
            security=[{'extra': []}, {'main': []}],
        )
        def get(self) -> str:
            raise NotImplementedError

    router = Router(
        'api/',
        [path('user/', _RegisteredOnlyController.as_view())],
    )

    with pytest.raises(
        EndpointMetadataError,
        match=r"Security schemes \['extra', 'main'\] are already generated",
    ):
        build_schema(router).convert()


def test_security_intersection_names_endpoint() -> None:
    """The intersection error names the endpoint that has it."""

    class _NamedIntersectionController(Controller[PydanticSerializer]):
        @modify(auth=[HeaderJWTSyncAuth()], security=[{'jwt': []}])
        def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match=r"endpoint_name=.*_NamedIntersectionController\.get'",
    ):
        build_schema(
            Router(
                'api/',
                [path('user/', _NamedIntersectionController.as_view())],
            ),
        ).convert()


@pytest.mark.usefixtures('_settings_jwt_security')
def test_settings_security_intersection_with_auth() -> None:
    """Settings level `security` cannot redefine schemes from `auth`."""

    class _SettingsIntersectionController(Controller[PydanticSerializer]):
        @modify(auth=[HeaderJWTSyncAuth()])
        def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match=r"Security schemes \['jwt'\] are already generated",
    ):
        build_schema(
            Router(
                'api/',
                [path('user/', _SettingsIntersectionController.as_view())],
            ),
        ).convert()


@pytest.mark.usefixtures('_settings_security')
def test_security_with_schema_only_auth() -> None:
    """Auth schemes are not touched when building the metadata."""

    class _SchemaOnlyController(Controller[PydanticSerializer]):
        @modify(auth=[_SchemaOnlyAuth()])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _SchemaOnlyController.api_endpoints['GET'].metadata

    assert metadata.security == [{'proxy': []}]


@pytest.mark.usefixtures('_settings_security')
def test_empty_security_keeps_other_levels() -> None:
    """Empty `security` adds nothing, but does not disable other levels."""

    class _EmptyLevelController(Controller[PydanticSerializer]):
        security = [{'gateway': []}]

        @modify(security=[])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _EmptyLevelController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}, {'proxy': []}]


def test_security_with_disabled_auth() -> None:
    """Disabling `auth` does not disable user provided `security`."""

    class _NoAuthController(Controller[PydanticSerializer]):
        @modify(auth=None, security=[{'gateway': []}])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _NoAuthController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}]


@pytest.mark.parametrize(
    ('wrong_security', 'reported'),
    [
        # `security` itself must be a list of requirements,
        # the whole value is reported in this case:
        pytest.param({'gateway': []}, "{'gateway': []}", id='single-mapping'),
        pytest.param({}, '{}', id='empty-mapping'),
        pytest.param('gateway', "'gateway'", id='string'),
        pytest.param('', "''", id='empty-string'),
        pytest.param(b'gateway', "b'gateway'", id='bytes'),
        # Requirements themselves must be dicts:
        pytest.param(
            [MappingProxyType({'gateway': []})],
            "[mappingproxy({'gateway': []})]",
            id='requirement-not-a-dict',
        ),
        pytest.param(
            [{'gateway': []}, 'gateway'],
            "[{'gateway': []}, 'gateway']",
            id='requirement-is-a-string',
        ),
    ],
)
def test_wrong_security_shape(wrong_security: object, reported: str) -> None:
    """Security must be a list of dicts of scheme names to lists of scopes."""
    security = cast('Sequence[SecurityRequirement]', wrong_security)

    with pytest.raises(
        EndpointMetadataError,
        match=rf'must be .*got {re.escape(reported)}.*endpoint_name',
    ):

        class _WrongShapeController(Controller[PydanticSerializer]):
            @modify(security=security)
            def get(self) -> str:
                raise NotImplementedError


def test_subclass_controller_security() -> None:
    """Subclasses inherit and can redefine `security` of the base."""

    class _BaseSecurityController(Controller[PydanticSerializer]):
        security = [{'gateway': []}]

        @modify()
        def get(self) -> str:
            raise NotImplementedError

    class _InheritedController(_BaseSecurityController):
        """Does not redefine anything."""

    class _RedefinedController(_BaseSecurityController):
        security = [{'mesh': []}]

    inherited = _InheritedController.api_endpoints['GET'].metadata
    redefined = _RedefinedController.api_endpoints['GET'].metadata

    assert inherited.security == [{'gateway': []}]
    assert redefined.security == [{'mesh': []}]
