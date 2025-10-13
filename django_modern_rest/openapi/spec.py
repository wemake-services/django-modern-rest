from collections.abc import Sequence
from typing import ClassVar

from django.urls import URLPattern, path

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.openapi.renderers import BaseRenderer
from django_modern_rest.openapi.schema import SchemaGenerator
from django_modern_rest.openapi.views import OpenAPIView
from django_modern_rest.routing import Router


class OpenAPISpec:
    """OpenAPI specification."""

    _name: ClassVar[str] = 'openapi'
    _schema_generator: type[SchemaGenerator] = SchemaGenerator

    def __init__(
        self,
        router: Router,
        renderers: Sequence[BaseRenderer],
        config: OpenAPIConfig | None = None,
    ) -> None:
        self.router = router
        self.config = config
        self.renderers = renderers

    def urls(self) -> tuple[list[URLPattern], str]:
        if self.config is None:
            self.config = self._default_config()

        # TODO: refactor this sh*t
        generator = self._schema_generator(self.config, self.router)

        urlpatterns = [
            path(
                renderer.path,
                OpenAPIView.as_view(
                    renderer=renderer,
                    schema=generator.to_schema(),
                ),
                name=f'{self._name}_{renderer.name}',
            )
            for renderer in self.renderers
        ]
        return (urlpatterns, self._name)

    @classmethod
    def _default_config(cls) -> OpenAPIConfig:
        # Circular import:
        from django_modern_rest.settings import (  # noqa: PLC0415
            DMR_OPENAPI_CONFIG_KEY,
            resolve_defaults,
        )

        config = resolve_defaults().get(DMR_OPENAPI_CONFIG_KEY)
        if not isinstance(config, OpenAPIConfig):
            raise TypeError(
                'OpenAPI config is not set. Please set the '
                "'DMR_OPENAPI_CONFIG' setting.",
            )
        return config
