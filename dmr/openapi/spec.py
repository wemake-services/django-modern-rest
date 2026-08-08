from typing import TYPE_CHECKING, overload

from dmr.openapi.config import OpenAPIConfig, default_config
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.openapi import OpenAPI

if TYPE_CHECKING:
    from dmr.routing import Router


@overload
def build_schema(router: 'Router', *, context: OpenAPIContext) -> OpenAPI: ...


@overload
def build_schema(
    router: 'Router',
    *,
    config: OpenAPIConfig | None = None,
) -> OpenAPI: ...


def build_schema(
    router: 'Router',
    *,
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
