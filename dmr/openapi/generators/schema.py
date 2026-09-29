import dataclasses
from typing import TYPE_CHECKING, Any, final

from dmr.exceptions import UnsolvableAnnotationsError
from dmr.internal.types import EMPTY
from dmr.openapi.mappers.example import (
    generate_example,
    set_generated_example,
)
from dmr.openapi.mappers.references import iter_references
from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.objects import Schema

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.core.registry import SchemaRegistry
    from dmr.serializer import BaseSerializer, SchemaDef


@final
@dataclasses.dataclass(frozen=True, slots=True)
class LoadedSchema:
    """
    Schema of an annotation together with all components it might use.

    Nothing from it is registered in the OpenAPI schema yet.
    Callers transform :attr:`schema` however they need
    and then pass the final result
    to :meth:`dmr.openapi.generators.SchemaGenerator.register`,
    which registers only the components that the result still references.

    .. versionadded:: 0.16.0
    """

    #: Schema of the annotation, it can reference :attr:`defs`
    #: with its ``$ref``.
    schema: Schema
    #: All components that :attr:`schema` might reference, by name.
    defs: dict[str, Schema]
    #: Annotation this schema was generated from.
    annotation: Any
    #: Name of the component in :attr:`defs`
    #: that describes the annotation itself, if there's one.
    name: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class SchemaGenerator:
    """
    Generate OpenAPI schemas from different type annotations.

    .. versionchanged:: 0.16.0
        Components are not registered while a schema is generated anymore.
        :meth:`load` returns a schema with all its components kept locally,
        :meth:`register` registers only the components that are referenced
        from the final result. Calling the generator does both at once.
        Removed ``skip_registration``
        and ``register_referenced_components`` parameters.
        References to components are returned as ``Schema`` objects
        with ``$ref`` set, not as ``Reference`` objects.

    """

    # Instance API:
    _context: 'OpenAPIContext'

    def __call__(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        *,
        used_for_response: bool = False,
    ) -> Schema:
        """
        Get schema for an annotation and register components it uses.

        Args:
            annotation: Type annotation to generate the schema for.
            serializer: Serializer that knows how to build
                a raw JSON schema from the annotation.
            used_for_response: Whether this schema describes a response,
                since some serializers generate different
                schemas for inputs and outputs.

        Raises:
            UnsolvableAnnotationsError: when we can't generate
                an OpenAPI schema from an existing annotation.

        """
        loaded = self.load(
            annotation,
            serializer,
            used_for_response=used_for_response,
        )
        self.register(loaded.schema, loaded)
        return loaded.schema

    def load(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        *,
        used_for_response: bool = False,
        inline: bool = False,
    ) -> LoadedSchema:
        """
        Get schema for an annotation without registering anything.

        Here's the algorithm we use:

        1. First, we try to find an existing reference in the registry
        2. Next, we get a raw JSON schema from the serializer.
           Models get their own components, so the result is a reference
        3. If nothing worked, we raise an error

        Args:
            annotation: Type annotation to generate the schema for.
            serializer: Serializer that knows how to build
                a raw JSON schema from the annotation.
            used_for_response: Whether this schema describes a response,
                since some serializers generate different
                schemas for inputs and outputs.
            inline: Resolve ``$ref`` in the result:
                the schema itself and members of its unions
                are replaced with their definitions.
                Useful when a schema's properties are needed.

        Raises:
            UnsolvableAnnotationsError: when we can't generate
                an OpenAPI schema from an existing annotation.

        .. versionadded:: 0.16.0
        """
        registry = self._context.registries.schema
        name = serializer.schema_generator.schema_name(annotation) or getattr(
            annotation,
            '__qualname__',
            None,
        )
        existing_reference = registry.get_reference(name, annotation)
        if existing_reference is None:
            loaded = self._load(annotation, serializer, used_for_response)
        else:
            loaded = LoadedSchema(existing_reference, {}, annotation, name)

        if inline:
            return dataclasses.replace(
                loaded,
                schema=_inline(loaded.schema, loaded.defs, registry),
            )
        return loaded

    def register(self, used: object, *loaded: LoadedSchema) -> None:
        """
        Register components of *loaded* schemas that are referenced from *used*.

        *used* is any OpenAPI object built from the loaded schemas,
        for example, the schema itself, a list of parameters,
        or a request body. Components that it references directly
        or through other referenced components are registered,
        all other components are dropped.

        .. versionadded:: 0.16.0
        """
        registry = self._context.registries.schema
        pending = set(iter_references(used, registry.schema_prefix))
        registered: set[str] = set()
        while pending:
            component_name = pending.pop()
            component = _find_component(component_name, loaded)
            if component is None or component_name in registered:
                # Not ours: it is already registered or comes from outside.
                continue
            registered.add(component_name)
            registry.register(component_name, *component)
            pending.update(
                iter_references(component[0], registry.schema_prefix),
            )

    def _load(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        used_for_response: bool,  # noqa: FBT001
    ) -> LoadedSchema:
        registry = self._context.registries.schema
        schema, defs = self._as_components(
            *_get_raw_schema(
                annotation,
                serializer,
                ref_template=registry.schema_prefix,
                used_for_response=used_for_response,
            ),
        )
        self._maybe_generate_example(
            registry.maybe_resolve_reference(schema, resolution_context=defs),
            annotation,
            serializer,
        )
        return LoadedSchema(
            schema,
            defs,
            annotation,
            _reference_name(schema, registry.schema_prefix),
        )

    def _as_components(
        self,
        raw_schema: dict[str, Any],
        raw_defs: dict[str, Any],
    ) -> tuple[Schema, dict[str, Schema]]:
        """Load raw schemas, the annotation's own model becomes a component."""
        defs = {
            component_name: load_schema(component)
            for component_name, component in raw_defs.items()
        }
        schema = load_schema(raw_schema)
        if schema.ref is not None or not schema.title:
            return schema, defs
        # Models are components, even when serializers inline them:
        defs[schema.title] = schema
        return Schema(
            ref=self._context.registries.schema.schema_prefix + schema.title,
        ), defs

    def _maybe_generate_example(
        self,
        schema: Schema,
        annotation: Any,
        serializer: type['BaseSerializer'],
    ) -> None:
        if schema.example is EMPTY and not schema.examples:  # pragma: no branch
            set_generated_example(
                schema,
                generate_example(annotation, serializer),
            )


def _get_raw_schema(
    annotation: Any,
    serializer: type['BaseSerializer'],
    *,
    ref_template: str,
    used_for_response: bool,
) -> 'SchemaDef':
    try:
        return serializer.schema_generator.get_schema(
            annotation,
            ref_template=ref_template,
            used_for_response=used_for_response,
        )
    except Exception as exc:
        raise UnsolvableAnnotationsError(
            f'Cannot generate OpenAPI schema from {annotation}, '
            'consider registering it as described in your serializer',
        ) from exc


def _inline(
    schema: Schema,
    defs: dict[str, Schema],
    registry: 'SchemaRegistry',
) -> Schema:
    """Resolve the schema and members of its unions from *defs*."""
    resolved = registry.maybe_resolve_reference(
        schema,
        resolution_context=defs,
    )
    if not resolved.any_of and not resolved.one_of and not resolved.all_of:
        return resolved
    # Copy the resolved schema, so the component itself is not changed:
    return dataclasses.replace(
        resolved,
        any_of=_inline_members(resolved.any_of, defs, registry),
        one_of=_inline_members(resolved.one_of, defs, registry),
        all_of=_inline_members(resolved.all_of, defs, registry),
    )


def _inline_members(
    members: list[Schema] | None,
    defs: dict[str, Schema],
    registry: 'SchemaRegistry',
) -> list[Schema] | None:
    if not members:
        return members
    return [_inline(member, defs, registry) for member in members]


def _reference_name(
    schema: Schema,
    schema_prefix: str,
) -> str | None:
    if schema.ref is not None:
        return schema.ref.removeprefix(schema_prefix)
    return None


def _find_component(
    component_name: str,
    loaded: tuple[LoadedSchema, ...],
) -> tuple[Schema, Any] | None:
    """Find a component with its annotation, if it describes the annotation."""
    for loaded_schema in loaded:
        component = loaded_schema.defs.get(component_name)
        if component is not None:
            return component, (
                loaded_schema.annotation
                if component_name == loaded_schema.name
                else EMPTY
            )
    return None
