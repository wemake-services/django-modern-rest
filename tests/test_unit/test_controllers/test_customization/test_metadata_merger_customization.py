from typing import Any, Final

from django.conf import LazySettings
from typing_extensions import Sentinel, override

from dmr import Controller, modify
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.settings import Settings
from dmr.validation import MetadataMerger

_SETTINGS_AUTH: Final = DjangoSessionSyncAuth()
_CONTROLLER_AUTH: Final = DjangoSessionSyncAuth()
_ENDPOINT_AUTH: Final = DjangoSessionSyncAuth()


class _MetadataMergerKeepAuth(MetadataMerger):
    """Merge ``auth`` from all layers, like it was done in ``0.15.0``."""

    @override
    def first_defined(
        self,
        *layers: Any,
    ) -> Any:
        # All non-auth fields must be handled in the default way:
        if self.field_name != 'auth':
            return super().first_defined(*layers)
        # Auth must be merged:
        if any(layer is None for layer in layers):
            return None  # explicit `None` disables auth on all layers
        return [
            auth
            for layer in layers
            if not isinstance(layer, Sentinel)
            for auth in layer
        ]


class _MergingEndpoint(Endpoint):
    metadata_merger_cls = _MetadataMergerKeepAuth


def test_custom_metadata_merger_cls(settings: LazySettings) -> None:
    """Ensure we can customize how endpoint, controller, settings are merged."""
    settings.DMR_SETTINGS = {Settings.auth: [_SETTINGS_AUTH]}

    class _Controller(Controller[PydanticSerializer]):
        endpoint_cls = _MergingEndpoint
        auth = (_CONTROLLER_AUTH,)
        tags = ['first']  # tags must not be merged

        @modify(auth=[_ENDPOINT_AUTH], tags=['second'])
        def get(self) -> str:
            raise NotImplementedError

        def post(self) -> str:
            raise NotImplementedError

        @modify(auth=None)
        def put(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.auth == [
        _ENDPOINT_AUTH,
        _CONTROLLER_AUTH,
        _SETTINGS_AUTH,
    ]
    assert _Controller.api_endpoints['GET'].metadata.tags == ['second']
    assert _Controller.api_endpoints['POST'].metadata.auth == [
        _CONTROLLER_AUTH,
        _SETTINGS_AUTH,
    ]
    assert _Controller.api_endpoints['POST'].metadata.tags == ['first']
    assert _Controller.api_endpoints['PUT'].metadata.auth is None
    assert _Controller.api_endpoints['PUT'].metadata.tags == ['first']
