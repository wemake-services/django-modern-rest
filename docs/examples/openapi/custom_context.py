from typing import ClassVar

from typing_extensions import override

from dmr.metadata import EndpointMetadata
from dmr.openapi import OpenAPIConfig, OpenAPIContext, build_schema
from dmr.openapi.core.merger import ConfigMerger
from dmr.openapi.generators import OperationIdGenerator
from dmr.openapi.objects import Components, Paths
from dmr.openapi.openapi import OpenAPI
from dmr.openapi.views import OpenAPIJsonView
from dmr.routing import Router, path
from dmr.serializer import BaseSerializer
from examples.getting_started.msgspec_controller import UserController


class PathOperationIdGenerator(OperationIdGenerator):
    """Generate IDs from the HTTP method and path, without controller names."""

    @override
    def __call__(
        self,
        path: str,
        suffix: str,
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
    ) -> str:
        # Keep explicit IDs and duplicate detection from the base generator:
        return super().__call__(path, '', metadata, serializer)


class CustomConfigMerger(ConfigMerger):
    """Post-process the merged specification without changing the config."""

    @override
    def __call__(self, paths: Paths, components: Components) -> OpenAPI:
        schema = super().__call__(paths, components)
        title = schema.info.title
        schema.info.title = f'{title} (custom)'
        return schema


class CustomContext(OpenAPIContext):
    operation_id_cls: ClassVar[type[OperationIdGenerator]] = (
        PathOperationIdGenerator
    )
    config_merger_cls: ClassVar[type[ConfigMerger]] = CustomConfigMerger


router = Router('api/', [path('user/', UserController.as_view())])
config = OpenAPIConfig(title='My API', version='1.0.0')
schema = build_schema(router, context=CustomContext(config))

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]

# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
