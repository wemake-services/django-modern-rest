import json
from typing import ClassVar, final

import pytest
from syrupy.assertion import SnapshotAssertion
from typing_extensions import override

from dmr import Controller, modify
from dmr.metadata import EndpointMetadata
from dmr.openapi import OpenAPIConfig, OpenAPIContext, build_schema
from dmr.openapi.core.merger import ConfigMerger
from dmr.openapi.generators import OperationIdGenerator
from dmr.openapi.objects import Components, Paths
from dmr.openapi.openapi import OpenAPI
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.routing import Router, path
from dmr.serializer import BaseSerializer


@final
class _PathOperationIdGenerator(OperationIdGenerator):
    @override
    def __call__(
        self,
        path: str,
        suffix: str,
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
    ) -> str:
        return super().__call__(path, '', metadata, serializer)


@final
class _CustomConfigMerger(ConfigMerger):
    @override
    def __call__(self, paths: Paths, components: Components) -> OpenAPI:
        schema = super().__call__(paths, components)
        title = schema.info.title
        schema.info.title = f'{title} (custom)'
        return schema


@final
class _CustomContext(OpenAPIContext):
    config_merger_cls: ClassVar[type[ConfigMerger]] = _CustomConfigMerger
    operation_id_cls: ClassVar[type[OperationIdGenerator]] = (
        _PathOperationIdGenerator
    )


@pytest.mark.parametrize(
    'serializer',
    [PydanticSerializer, PydanticFastSerializer],
)
def test_custom_context_schema(
    serializer: type[BaseSerializer],
    snapshot: SnapshotAssertion,
) -> None:
    """Custom context changes the schema and preserves the input config."""

    class _UserController(Controller[serializer]):  # type: ignore[valid-type]
        def get(self) -> int:
            raise NotImplementedError

        @modify(operation_id='ExplicitCreate')
        def post(self) -> int:
            raise NotImplementedError

    router = Router('api/', [path('users/', _UserController.as_view())])
    config = OpenAPIConfig(title='Users API', version='1.0.0')
    custom_schema = build_schema(
        router,
        context=_CustomContext(config),
    ).convert()

    assert json.dumps(custom_schema, indent=2) == snapshot
    assert config.title == 'Users API'
