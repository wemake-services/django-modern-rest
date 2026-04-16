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
        {'throttling': ['throttling']},
        {'responses': [{}]},
        {'openapi_config': []},
        {'global_error_handler': None},
        {'exclude_semantic_responses': 1},
    ],
)
@pytest.mark.parametrize('serializer', serializers)
def test_wrong_settings_validation(
    settings: LazySettings,
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
        # Extras:
        {},
        {'extra': True},
        # Values:
        {'no_validate_http_spec': set()},
        {'no_validate_http_spec': frozenset()},
        {'exclude_semantic_responses': set()},
        {'exclude_semantic_responses': frozenset()},
    ],
)
@pytest.mark.parametrize('serializer', serializers)
def test_correct_settings_validation(
    settings: LazySettings,
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
