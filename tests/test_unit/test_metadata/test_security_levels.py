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


def _config(security: list[SecurityRequirement]) -> OpenAPIConfig:
    return OpenAPIConfig(
        title='Security API',
        version='1.0.0',
        security=security,
    )


@pytest.fixture
def _settings_security(settings: LazySettings) -> None:
    settings.DMR_SETTINGS = {
        Settings.openapi_config: _config([{'proxy': []}]),
    }


@pytest.fixture
def _settings_jwt_security(settings: LazySettings) -> None:
    settings.DMR_SETTINGS = {
        Settings.openapi_config: _config([{'jwt': []}]),
    }


def _operation_security(
    controller_cls: type[Controller[PydanticSerializer]],
    method: str = 'get',
) -> list[SecurityRequirement] | None:
    schema = build_schema(
        Router('api/', [path('user/', controller_cls.as_view())]),
    ).convert()
    return schema['paths']['/api/user/'][method].get(  # type: ignore[no-any-return]
        'security',
    )


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
    """Endpoints without decorators also get the settings level."""

    class _RawSettingsController(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    metadata = _RawSettingsController.api_endpoints['GET'].metadata

    assert metadata.security == [{'proxy': []}]


@pytest.mark.usefixtures('_settings_security')
def test_settings_security() -> None:
    """`OpenAPIConfig.security` from settings is applied to all endpoints."""

    class _SettingsController(Controller[PydanticSerializer]):
        @modify()
        def get(self) -> str:
            raise NotImplementedError

    metadata = _SettingsController.api_endpoints['GET'].metadata

    assert metadata.security == [{'proxy': []}]


@pytest.mark.usefixtures('_settings_security')
def test_endpoint_security_wins() -> None:
    """The endpoint level wins over the controller and settings levels."""

    class _EndpointWinsController(Controller[PydanticSerializer]):
        security = [{'controller': []}]

        @modify(security=[{'endpoint': []}])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _EndpointWinsController.api_endpoints['GET'].metadata

    assert metadata.security == [{'endpoint': []}]


@pytest.mark.usefixtures('_settings_security')
def test_controller_security_wins_over_settings() -> None:
    """The controller level wins over the settings level."""

    class _ControllerWinsController(Controller[PydanticSerializer]):
        security = [{'controller': []}]

        @modify()
        def get(self) -> str:
            raise NotImplementedError

    metadata = _ControllerWinsController.api_endpoints['GET'].metadata

    assert metadata.security == [{'controller': []}]


@pytest.mark.usefixtures('_settings_security')
@pytest.mark.parametrize('security_def', [None, [], ()])
def test_endpoint_security_disables_security(
    *,
    security_def: Any,
) -> None:
    """Empty `security` on the endpoint disables all inherited requirements."""

    class _DisabledEndpointController(Controller[PydanticSerializer]):
        security = [{'gateway': []}]

        @modify(security=security_def)
        def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledEndpointController.api_endpoints['GET'].metadata

    assert metadata.security is None


@pytest.mark.parametrize('auth_def', [None, [], ()])
def test_endpoint_empty_auth_disables(
    *,
    auth_def: Any,
) -> None:
    """Empty `auth` on the endpoint disables all."""

    class _DisabledEndpointController(Controller[PydanticSerializer]):
        auth = [HeaderJWTSyncAuth()]

        @modify(auth=auth_def)  # type: ignore[untyped-decorator]
        def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledEndpointController.api_endpoints['GET'].metadata

    assert metadata.auth is None


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
def test_endpoint_security_over_controller_none() -> None:
    """Endpoint level is more specific than the controller's `None`."""

    class _EnabledEndpointController(Controller[PydanticSerializer]):
        security = None

        @modify(security=[{'gateway': []}])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _EnabledEndpointController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}]


@pytest.mark.parametrize('empty', [[], ()])
def test_empty_security_adds_nothing(
    empty: Sequence[SecurityRequirement],
) -> None:
    """Empty `security` means that no security is configured."""

    class _EmptyController(Controller[PydanticSerializer]):
        @modify(security=empty)
        def get(self) -> str:
            raise NotImplementedError

    metadata = _EmptyController.api_endpoints['GET'].metadata

    assert metadata.security is None


@pytest.mark.usefixtures('_settings_security')
@pytest.mark.parametrize('empty', [[], ()])
def test_empty_security_disables_next_level(
    empty: Sequence[SecurityRequirement],
) -> None:
    """Empty `security` is explicit, it disables all less specific levels."""

    class _EmptyEndpointController(Controller[PydanticSerializer]):
        security = [{'gateway': []}]

        @modify(security=empty)
        def get(self) -> str:
            raise NotImplementedError

    class _EmptyControllerController(Controller[PydanticSerializer]):
        security = empty

        @modify()
        def get(self) -> str:
            raise NotImplementedError

    empty_endpoint = _EmptyEndpointController.api_endpoints['GET'].metadata
    empty_controller = _EmptyControllerController.api_endpoints['GET'].metadata

    assert empty_endpoint.security is None
    assert empty_controller.security is None


@pytest.mark.usefixtures('_settings_security')
@pytest.mark.parametrize('empty', [[], ()])
def test_empty_security_is_none(
    empty: Sequence[SecurityRequirement],
) -> None:
    """Empty `security` and `None` produce the same schema."""

    class _EmptyController(Controller[PydanticSerializer]):
        @modify(security=empty)
        def get(self) -> str:
            raise NotImplementedError

    class _NoneController(Controller[PydanticSerializer]):
        @modify(security=None)
        def get(self) -> str:
            raise NotImplementedError

    assert _EmptyController.api_endpoints['GET'].metadata.security is None
    assert _NoneController.api_endpoints['GET'].metadata.security is None
    assert _operation_security(_EmptyController) == []
    assert _operation_security(_NoneController) == []


@pytest.mark.parametrize('empty', [[], ()])
def test_empty_settings_security_disables(
    settings: LazySettings,
    empty: Sequence[SecurityRequirement],
) -> None:
    """Empty `OpenAPIConfig.security` means no security at all."""
    settings.DMR_SETTINGS = {
        Settings.openapi_config: _config(list(empty)),
    }

    class _EmptySettingsController(Controller[PydanticSerializer]):
        @modify()
        def get(self) -> str:
            raise NotImplementedError

    metadata = _EmptySettingsController.api_endpoints['GET'].metadata

    assert metadata.security is None
    assert _operation_security(_EmptySettingsController) is None


@pytest.mark.usefixtures('_settings_security')
def test_security_with_schema_only_auth() -> None:
    """Auth schemes are not touched when building the metadata."""

    class _SchemaOnlyController(Controller[PydanticSerializer]):
        @modify(auth=[_SchemaOnlyAuth()])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _SchemaOnlyController.api_endpoints['GET'].metadata

    assert metadata.security == [{'proxy': []}]


def test_security_with_disabled_auth() -> None:
    """Disabling `auth` does not disable user provided `security`."""

    class _NoAuthController(Controller[PydanticSerializer]):
        @modify(auth=None, security=[{'gateway': []}])
        def get(self) -> str:
            raise NotImplementedError

    metadata = _NoAuthController.api_endpoints['GET'].metadata

    assert metadata.security == [{'gateway': []}]


def test_security_is_merged_with_auth() -> None:
    """User provided `security` is added after the `auth` requirements."""

    class _MergedController(Controller[PydanticSerializer]):
        @modify(auth=[_TwoSchemesAuth()], security=[{'gateway': []}])
        def get(self) -> str:
            raise NotImplementedError

    assert _operation_security(_MergedController) == [
        {'main': []},
        {'gateway': []},
    ]


@pytest.mark.usefixtures('_settings_security')
def test_settings_security_is_merged_with_auth() -> None:
    """Settings level `security` is merged with `auth` as well."""

    class _SettingsMergedController(Controller[PydanticSerializer]):
        @modify(auth=[_TwoSchemesAuth()])
        def get(self) -> str:
            raise NotImplementedError

    assert _operation_security(_SettingsMergedController) == [
        {'main': []},
        {'proxy': []},
    ]


@pytest.mark.usefixtures('_settings_security')
def test_settings_security_without_auth() -> None:
    """Endpoints without `auth` still get the settings level `security`."""

    class _SettingsOnlyController(Controller[PydanticSerializer]):
        @modify()
        def get(self) -> str:
            raise NotImplementedError

    assert _operation_security(_SettingsOnlyController) == [{'proxy': []}]


@pytest.mark.usefixtures('_settings_security')
def test_disabled_security_opts_out_of_global() -> None:
    """`security=None` without `auth` opts out of the global requirements."""

    class _OptOutController(Controller[PydanticSerializer]):
        @modify(security=None)
        def get(self) -> str:
            raise NotImplementedError

    assert _operation_security(_OptOutController) == []


def test_security_can_reuse_auth_schemes() -> None:
    """Schemes registered by `auth` can be used in `security` requirements."""

    class _ReuseSchemeController(Controller[PydanticSerializer]):
        @modify(auth=[_TwoSchemesAuth()], security=[{'extra': []}])
        def get(self) -> str:
            raise NotImplementedError

    schema = build_schema(
        Router('api/', [path('user/', _ReuseSchemeController.as_view())]),
    ).convert()

    assert schema['paths']['/api/user/']['get']['security'] == [
        {'main': []},
        {'extra': []},
    ]
    assert set(schema['components']['securitySchemes']) == {'main', 'extra'}


@pytest.mark.parametrize(
    'security_def',
    [
        [{'jwt': []}],
        [{'jwt': []}, {'jwt': []}],
        [{'jwt': ['claim1']}, {'jwt': ['claim1']}],
    ],
)
def test_security_duplicates_auth_requirement(*, security_def: Any) -> None:
    """Requirements from `auth` cannot be repeated in `security`."""

    class _DuplicateController(Controller[PydanticSerializer]):
        @modify(auth=[HeaderJWTSyncAuth()], security=security_def)
        def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(EndpointMetadataError, match='jwt'):
        _operation_security(_DuplicateController)


def test_security_duplicates_itself() -> None:
    """The same requirement cannot be repeated inside `security`."""

    class _RepeatedController(Controller[PydanticSerializer]):
        @modify(security=[{'gateway': []}, {'mesh': []}, {'gateway': []}])
        def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(EndpointMetadataError, match='gateway'):
        _operation_security(_RepeatedController)


@pytest.mark.usefixtures('_settings_jwt_security')
def test_settings_security_duplicates_auth() -> None:
    """Settings level `security` cannot repeat requirements from `auth`."""

    class _SettingsDuplicateController(Controller[PydanticSerializer]):
        @modify(auth=[HeaderJWTSyncAuth()])
        def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(EndpointMetadataError, match='jwt'):
        _operation_security(_SettingsDuplicateController)


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
def test_wrong_security_shape(
    *,
    wrong_security: Any,
    reported: str,
) -> None:
    """Security must be a list of dicts of scheme names to lists of scopes."""
    with pytest.raises(EndpointMetadataError, match='must be a sequence'):

        class _WrongShapeController(Controller[PydanticSerializer]):
            @modify(security=wrong_security)
            def get(self) -> str:
                raise NotImplementedError


def test_wrong_controller_security_shape() -> None:
    """Controller level `security` is validated even when it is overridden."""
    with pytest.raises(EndpointMetadataError, match='must be a sequence'):

        class _WrongControllerController(Controller[PydanticSerializer]):
            security = {'gateway': []}  # type: ignore[var-annotated, assignment]

            @modify(security=[{'mesh': []}])
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
