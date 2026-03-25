from typing import TYPE_CHECKING

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.objects import OpenAPI

if TYPE_CHECKING:
    from dmr.routing import Router


def build_schema(
    router: 'Router',
    *,
    # TODO: this can be an overloaded function:
    context: OpenAPIContext | None = None,
    config: OpenAPIConfig | None = None,
) -> OpenAPI:
    """
    Build OpenAPI schema.

    Parameters:
        router: Router that contains all API endpoints and all controllers.
        context: OpenAPI context with all the builder tools.
        config: Optional configuration of OpenAPI metadata.
            Can be ``None``, in this case we fetch OpenAPI config from settings.

    """
    if context and config:
        raise ValueError('Passing both `config` and `context` is not supported')
    if context is None:
        context = OpenAPIContext(config=config or default_config())
    return router.get_schema(context)


def default_config() -> OpenAPIConfig:
    """Resolves the default config from settings."""
    from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

    config = resolve_setting(Settings.openapi_config)
    if not isinstance(config, OpenAPIConfig):
        raise TypeError(
            'OpenAPI config is not set. Please, set the '
            f'{str(Settings.openapi_config)!r} setting.',
        )
    return config
