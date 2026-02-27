from typing import TYPE_CHECKING

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.builder import OpenAPIBuilder
from dmr.openapi.core.context import OpenAPIContext

if TYPE_CHECKING:
    from dmr.openapi.objects import OpenAPI
    from dmr.routing import Router


def build_schema(
    router: 'Router',
    *,
    config: OpenAPIConfig | None = None,
) -> 'OpenAPI':
    """
    Build OpenAPI schema.

    Parameters:
        router: Router that contains all API endpoints and all controllers.
        config: Optional configuration of OpenAPI metadata.
            Can be ``None``, in this case we fetch OpenAPI config from settings.

    """
    context = OpenAPIContext(config=config or _default_config())
    return OpenAPIBuilder(context)(router)


def _default_config() -> OpenAPIConfig:
    from dmr.settings import (  # noqa: PLC0415
        Settings,
        resolve_setting,
    )

    config = resolve_setting(Settings.openapi_config)
    if not isinstance(config, OpenAPIConfig):
        raise TypeError(
            'OpenAPI config is not set. Please, set the '
            f'{str(Settings.openapi_config)!r} setting.',
        )
    return config
