from typing import Any, Final, TypeAlias

import pytest
from django.conf import LazySettings

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.validation import SettingsValidator

_Serializes: TypeAlias = list[type[BaseSerializer]]
serializers: Final[_Serializes] = [
    PydanticSerializer,
]

try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pass  # noqa: WPS420
else:  # pragma: no cover
    serializers.append(MsgspecSerializer)


@pytest.fixture(autouse=True)
def _reset_settings_validation(dmr_clean_settings: None) -> None:
    SettingsValidator.is_validated = False


@pytest.mark.parametrize(
    'dmr_settings',
    [
        # Structure:
        {'validate_responses': None},
        {'responses': {}},
        # Instances:
        {'parsers': [1]},
        {'renderers': [None]},
        {'auth': ['auth']},
        {'responses': [{}]},
        {'openapi_config': []},
        {'global_error_handler': None},
    ],
)
@pytest.mark.parametrize('serializer', serializers)
def test_wrong_settings_validation(
    settings: LazySettings,
    dmr_clean_settings: None,
    *,
    dmr_settings: dict[str, Any],
    serializer: type[BaseSerializer],
) -> None:
    """Ensures invalid settings raise an error."""
    settings.DMR_SETTINGS = dmr_settings

    with pytest.raises(EndpointMetadataError, match='Settings'):

        class _ValidController(Controller[serializer]):  # type: ignore[valid-type]
            def post(self) -> int:
                raise NotImplementedError


@pytest.mark.parametrize(
    'dmr_settings',
    [
        # Structure:
        {},
        {'extra': True},
    ],
)
@pytest.mark.parametrize('serializer', serializers)
def test_correct_settings_validation(
    settings: LazySettings,
    dmr_clean_settings: None,
    *,
    dmr_settings: dict[str, Any],
    serializer: type[BaseSerializer],
) -> None:
    """Ensures correct settings passes."""
    settings.DMR_SETTINGS = dmr_settings

    class _ValidController(Controller[serializer]):  # type: ignore[valid-type]
        def post(self) -> int:
            raise NotImplementedError


@pytest.mark.parametrize('serializer', serializers)
def test_default_settings_validation(
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures default settings passes."""
    del settings.DMR_SETTINGS  # noqa: WPS420

    class _ValidController(Controller[serializer]):  # type: ignore[valid-type]
        def post(self) -> int:
            raise NotImplementedError
