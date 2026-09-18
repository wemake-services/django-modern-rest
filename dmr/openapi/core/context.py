from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, get_origin

from dmr.openapi.core.merger import ConfigMerger
from dmr.openapi.core.registry import (
    OperationIdRegistry,
    SchemaCallback,
    SchemaRegistry,
    SecuritySchemeRegistry,
)
from dmr.openapi.generators import (
    ComponentParserGenerator,
    OperationIdGenerator,
    ParameterGenerator,
    ResponseGenerator,
    SchemaGenerator,
    SecuritySchemeGenerator,
)
from dmr.openapi.mappers.example import seed_example_factory
from dmr.openapi.objects import Components, Reference, Schema

if TYPE_CHECKING:
    from dmr.openapi.config import OpenAPIConfig


@dataclass(slots=True, frozen=True)
class RegistryContainer:
    """Container for registries."""

    operation_id: OperationIdRegistry
    schema: SchemaRegistry
    security_scheme: SecuritySchemeRegistry


@dataclass(slots=True, frozen=True)
class GeneratorContainer:
    """Container for generators."""

    operation_id: OperationIdGenerator
    schema: SchemaGenerator
    component_parsers: ComponentParserGenerator
    response: ResponseGenerator
    security_scheme: SecuritySchemeGenerator
    parameter: ParameterGenerator


class OpenAPIContext:
    """
    Context for OpenAPI specification generation.

    Maintains shared state and generators used across the OpenAPI
    generation process. Provides access to different generators.

    Subclass this context and override the ``*_cls`` attributes to customize
    schema generation. Each class is instantiated with the current context.

    .. versionchanged:: 0.16.0
        Added class-level overrides for generators and the configuration merger.

    .. versionchanged:: 0.16.0
        Added the :meth:`seed_examples` hook.

    """

    __slots__ = (
        'config',
        'config_merger',
        'generators',
        'registries',
    )

    #: Merges configuration with generated paths and components.
    config_merger_cls: ClassVar[type[ConfigMerger]] = ConfigMerger
    #: Generates and registers operation IDs.
    operation_id_cls: ClassVar[type[OperationIdGenerator]] = (
        OperationIdGenerator
    )
    #: Resolves annotations into schemas and references.
    schema_cls: ClassVar[type[SchemaGenerator]] = SchemaGenerator
    #: Generates request bodies and parameters from endpoint components.
    component_parsers_cls: ClassVar[type[ComponentParserGenerator]] = (
        ComponentParserGenerator
    )
    #: Generates endpoint responses.
    response_cls: ClassVar[type[ResponseGenerator]] = ResponseGenerator
    #: Generates security requirements and registers security schemes.
    security_scheme_cls: ClassVar[type[SecuritySchemeGenerator]] = (
        SecuritySchemeGenerator
    )
    #: Generates parameters from models.
    parameter_cls: ClassVar[type[ParameterGenerator]] = ParameterGenerator

    def __init__(
        self,
        config: 'OpenAPIConfig | None' = None,
    ) -> None:
        """Initialize the OpenAPI context."""
        from dmr.openapi.config import default_config  # noqa: PLC0415

        self.config = config or default_config()
        self.config_merger = self.config_merger_cls(self)

        # Initialize registries:
        self.registries = RegistryContainer(
            operation_id=OperationIdRegistry(),
            schema=SchemaRegistry(),
            security_scheme=SecuritySchemeRegistry(),
        )

        # Initialize generators:
        self.generators = GeneratorContainer(
            operation_id=self.operation_id_cls(self),
            schema=self.schema_cls(self),
            component_parsers=self.component_parsers_cls(self),
            response=self.response_cls(self),
            security_scheme=self.security_scheme_cls(self),
            parameter=self.parameter_cls(self),
        )

        # Last, so that overrides of this method see a ready context:
        self.seed_examples()

    def seed_examples(self) -> None:
        """
        Seed the generation of examples for this schema.

        One context builds one schema, so this runs exactly once per schema.
        All its examples then come from a single random stream, which is
        what makes them differ from each other.

        Override it to seed from something other than
        :data:`~dmr.settings.Settings.openapi_examples_seed`,
        or to leave the factory alone entirely.

        .. versionadded:: 0.16.0
        """
        seed_example_factory()

    def get_components(self) -> Components:
        """
        Resolve all components from own and external schemas.

        .. versionadded:: 0.13.0
        """
        return Components(
            # TODO: support other components, not just `schema`:
            schemas=self.registries.schema.schemas or None,
            security_schemes=self.registries.security_scheme.schemes or None,
        )

    def register_schema(
        self,
        annotation: Any,
        schema: Reference | Schema | SchemaCallback,
        *,
        override: bool = False,
    ) -> None:
        """
        Register top-level annotation resolution into an OpenAPI schema.

        You can pass either a schema object itself, a reference, or a callback
        that returns schema, reference, or ``None`` to fallback
        to the default schema resolution process.

        .. warning::

            This only works for the top-level annotations with direct matches.
            For example: when you register ``User`` to have a specific schema,
            it will take effect only in cases where ``User`` is used directly.
            ``list[User]`` will use the default serializer
            schema resolution strategy.

        """
        real_type = get_origin(annotation) or annotation
        if not override and real_type in self.registries.schema.overrides:
            raise ValueError(f'{real_type} is already registered')
        self.registries.schema.overrides[real_type] = schema
