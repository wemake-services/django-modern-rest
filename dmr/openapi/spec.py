from typing import TYPE_CHECKING

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.builder import OpenAPIBuilder
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.objects import OpenAPI

if TYPE_CHECKING:
    from dmr.routing import Router


def build_schema(
    router: 'Router',
    *,
    config: OpenAPIConfig | None = None,
    builder: type[OpenAPIBuilder] = OpenAPIBuilder,
) -> OpenAPI:
    """
    Build OpenAPI schema.

    Parameters:
        router: Router that contains all API endpoints and all controllers.
        config: Optional configuration of OpenAPI metadata.
            Can be ``None``, in this case we fetch OpenAPI config from settings.
        builder: ``OpenAPIBuilder`` subclass to build the API.

    """
    context = OpenAPIContext(config=config or _default_config())
    return builder(context)(router)


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
