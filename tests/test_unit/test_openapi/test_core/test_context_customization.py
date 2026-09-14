from typing import ClassVar, Final, TypeAlias, final

import pytest
from typing_extensions import override

from dmr import Controller, modify
from dmr.metadata import EndpointMetadata
from dmr.openapi import OpenAPIConfig, OpenAPIContext, build_schema
from dmr.openapi.core.merger import ConfigMerger
from dmr.openapi.generators import (
    ComponentParserGenerator,
    OperationIdGenerator,
    ParameterGenerator,
    ResponseGenerator,
    SchemaGenerator,
    SecuritySchemeGenerator,
)
from dmr.openapi.objects import Components, Paths
from dmr.openapi.openapi import OpenAPI
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.routing import Router, path
from dmr.serializer import BaseSerializer

_Serializers: TypeAlias = list[type[BaseSerializer]]
serializers: Final[_Serializers] = [
    PydanticSerializer,
    PydanticFastSerializer,
]
try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pass  # noqa: WPS420
else:  # pragma: no cover
    serializers.append(MsgspecSerializer)


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
class _CustomSchemaGenerator(SchemaGenerator):
    """A user-provided schema generator."""


@final
class _CustomComponentParserGenerator(ComponentParserGenerator):
    """A user-provided component parser generator."""


@final
class _CustomResponseGenerator(ResponseGenerator):
    """A user-provided response generator."""


@final
class _CustomSecuritySchemeGenerator(SecuritySchemeGenerator):
    """A user-provided security scheme generator."""


@final
class _CustomParameterGenerator(ParameterGenerator):
    """A user-provided parameter generator."""


@final
class _CustomContext(OpenAPIContext):
    config_merger_cls: ClassVar[type[ConfigMerger]] = _CustomConfigMerger
    operation_id_cls: ClassVar[type[OperationIdGenerator]] = (
        _PathOperationIdGenerator
    )
    schema_cls: ClassVar[type[SchemaGenerator]] = _CustomSchemaGenerator
    component_parsers_cls: ClassVar[type[ComponentParserGenerator]] = (
        _CustomComponentParserGenerator
    )
    response_cls: ClassVar[type[ResponseGenerator]] = _CustomResponseGenerator
    security_scheme_cls: ClassVar[type[SecuritySchemeGenerator]] = (
        _CustomSecuritySchemeGenerator
    )
    parameter_cls: ClassVar[type[ParameterGenerator]] = (
        _CustomParameterGenerator
    )


@pytest.mark.parametrize(
    ('name', 'custom_cls', 'default_cls'),
    [
        ('operation_id', _PathOperationIdGenerator, OperationIdGenerator),
        ('schema', _CustomSchemaGenerator, SchemaGenerator),
        (
            'component_parsers',
            _CustomComponentParserGenerator,
            ComponentParserGenerator,
        ),
        ('response', _CustomResponseGenerator, ResponseGenerator),
        (
            'security_scheme',
            _CustomSecuritySchemeGenerator,
            SecuritySchemeGenerator,
        ),
        ('parameter', _CustomParameterGenerator, ParameterGenerator),
    ],
)
def test_generator_classes(
    name: str,
    custom_cls: type[object],
    default_cls: type[object],
) -> None:
    """Overrides apply per context without changing the default factories."""
    context = _CustomContext()
    other_context = _CustomContext()

    generator = getattr(context.generators, name)

    assert isinstance(generator, custom_cls)
    assert generator is not getattr(other_context.generators, name)
    default_generator = getattr(OpenAPIContext().generators, name)
    assert isinstance(default_generator, default_cls)
    assert not isinstance(default_generator, custom_cls)


def test_config_merger_class() -> None:
    """Each custom merger is bound to the context that created it."""
    context = _CustomContext()
    other_context = _CustomContext()

    assert isinstance(context.config_merger, _CustomConfigMerger)
    assert context.config_merger.context is context
    assert other_context.config_merger.context is other_context
    assert isinstance(OpenAPIContext().config_merger, ConfigMerger)
    assert not isinstance(OpenAPIContext().config_merger, _CustomConfigMerger)


@pytest.mark.parametrize('serializer', serializers)
def test_custom_context_schema(serializer: type[BaseSerializer]) -> None:
    """Customizations preserve explicit IDs, config, and other schema fields."""

    class _UserController(Controller[serializer]):  # type: ignore[valid-type]
        def get(self) -> int:
            raise NotImplementedError

        @modify(operation_id='ExplicitCreate')
        def post(self) -> int:
            raise NotImplementedError

    router = Router('api/', [path('users/', _UserController.as_view())])
    config = OpenAPIConfig(title='Users API', version='1.0.0')
    default_schema = build_schema(router, config=config).convert()

    custom_schema = build_schema(
        router,
        context=_CustomContext(config),
    ).convert()

    assert custom_schema['paths']['/api/users/']['get']['operationId'] == (
        'getApiUsers'
    )
    assert custom_schema['paths']['/api/users/']['post']['operationId'] == (
        'ExplicitCreate'
    )
    assert custom_schema['info']['title'] == 'Users API (custom)'
    assert config.title == 'Users API'
    # A fresh context must not inherit another context's IDs or factories:
    assert build_schema(router, context=_CustomContext(config)).convert() == (
        custom_schema
    )
    assert build_schema(router, config=config).convert() == default_schema
    # Everything except the intentionally customized fields stays the same:
    default_schema['info']['title'] = 'Users API (custom)'
    default_schema['paths']['/api/users/']['get']['operationId'] = 'getApiUsers'
    assert custom_schema == default_schema


@pytest.mark.parametrize('serializer', serializers)
def test_custom_generated_id_collision(
    serializer: type[BaseSerializer],
) -> None:
    """Custom-generated IDs still use the shared uniqueness registry."""

    class _UserController(Controller[serializer]):  # type: ignore[valid-type]
        def get(self) -> int:
            raise NotImplementedError

    router = Router(
        'api/',
        [
            path('user-profile/', _UserController.as_view()),
            path('user_profile/', _UserController.as_view()),
        ],
    )

    with pytest.raises(ValueError, match="'getApiUserProfile' is already"):
        build_schema(router, context=_CustomContext())


@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.parametrize('explicit_first', [True, False])
def test_custom_and_explicit_id_collision(
    serializer: type[BaseSerializer],
    *,
    explicit_first: bool,
) -> None:
    """Explicit and custom-generated IDs conflict in either traversal order."""

    class _UserController(Controller[serializer]):  # type: ignore[valid-type]
        def get(self) -> int:
            raise NotImplementedError

    class _ExplicitController(Controller[serializer]):  # type: ignore[valid-type]
        @modify(operation_id='getApiUsers')
        def get(self) -> int:
            raise NotImplementedError

    routes = [
        path('manual/', _ExplicitController.as_view()),
        path('users/', _UserController.as_view()),
    ]
    if not explicit_first:
        routes.reverse()

    with pytest.raises(ValueError, match="'getApiUsers' is already"):
        build_schema(Router('api/', routes), context=_CustomContext())
