from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, get_origin

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
    """

    __slots__ = (
        'config',
        'config_merger',
        'external_components',
        'generators',
        'registries',
    )

    def __init__(
        self,
        config: 'OpenAPIConfig',
    ) -> None:
        """Initialize the OpenAPI context."""
        self.config = config
        self.config_merger = ConfigMerger(self)
        self.external_components: Components | None = None

        # Initialize registries:
        self.registries = RegistryContainer(
            operation_id=OperationIdRegistry(),
            schema=SchemaRegistry(),
            security_scheme=SecuritySchemeRegistry(),
        )

        # Initialize generators:
        self.generators = GeneratorContainer(
            operation_id=OperationIdGenerator(self),
            schema=SchemaGenerator(self),
            component_parsers=ComponentParserGenerator(self),
            response=ResponseGenerator(self),
            security_scheme=SecuritySchemeGenerator(self),
            parameter=ParameterGenerator(self),
        )

    def get_components(self) -> Components:
        """
        Resolve all components from own and external schemas.

        .. versionadded:: 0.13.0
        """
        components = Components(
            # TODO: support other components, not just `schema`:
            schemas=self.registries.schema.schemas,
            security_schemes=self.registries.security_scheme.schemes,
        )
        if self.external_components is None:
            return components
        return self._merge_components(
            components,
            self.external_components,
        )

    def register_schema(
        self,
        annotation: Any,
        schema: Schema | Reference | SchemaCallback,
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

    def register_external_schemas(self, components: Components) -> None:
        """
        Register schemas from external OpenAPI definition.

        .. versionadded:: 0.13.0
        """
        self.external_components = self._merge_components(
            self.external_components,
            components,
        )

    def _merge_components(
        self,
        existing: Components | None,
        to_merge: Components,
    ) -> Components:
        """
        Merges two components together.

        Also ensures that no schemas overwrite each other in both components.

        .. versionadded:: 0.13.0
        """
        if existing is None:
            return to_merge
        return Components(
            schemas=_merge_unique(existing.schemas, to_merge.schemas),
            responses=_merge_unique(existing.responses, to_merge.responses),
            parameters=_merge_unique(existing.parameters, to_merge.parameters),
            examples=_merge_unique(existing.examples, to_merge.examples),
            request_bodies=_merge_unique(
                existing.request_bodies,
                to_merge.request_bodies,
            ),
            headers=_merge_unique(existing.headers, to_merge.headers),
            security_schemes=_merge_unique(
                existing.security_schemes,
                to_merge.security_schemes,
            ),
            links=_merge_unique(existing.links, to_merge.links),
            callbacks=_merge_unique(existing.callbacks, to_merge.callbacks),
            path_items=_merge_unique(existing.path_items, to_merge.path_items),
        )


_ThingT = TypeVar('_ThingT')


def _merge_unique(
    existing: dict[str, _ThingT] | None,
    to_merge: dict[str, _ThingT] | None,
) -> dict[str, _ThingT] | None:
    if existing is None:
        return to_merge
    if to_merge is None:
        return None

    shared_keys = existing.keys() & to_merge.keys()
    if shared_keys:
        raise ValueError(
            f'Trying to merge components with shared keys: {shared_keys}',
        )
    return {**existing, **to_merge}
