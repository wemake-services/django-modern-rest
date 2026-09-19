import dataclasses
from typing import TYPE_CHECKING, Any, Literal, overload

from dmr.exceptions import UnsolvableAnnotationsError
from dmr.openapi.mappers.example import (
    generate_example,
    set_generated_example,
)
from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.objects import Reference, Schema

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True)
class SchemaGenerator:
    """Generate OpenAPI schemas from different type annotations."""

    # Instance API:
    _context: 'OpenAPIContext'

    @overload
    def __call__(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        *,
        used_for_response: bool = False,
        skip_registration: Literal[True],
        register_referenced_components: bool = False,
    ) -> Schema: ...

    @overload
    def __call__(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        *,
        used_for_response: bool = False,
        skip_registration: bool = False,
        register_referenced_components: bool = False,
    ) -> Reference | Schema: ...

    def __call__(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        *,
        used_for_response: bool = False,
        skip_registration: bool = False,
        register_referenced_components: bool = False,
    ) -> Reference | Schema:
        """
        Get schema for an annotation.

        Here's the algorithm we use:

        1. First, we try to find any existing schema references from cache
        2. Next, we try to get a model schema from a serializer.
           If it exists, we create an internal reference and return it.
           The next time it will be returned as a reference, cached.
        3. If nothing worked, we raise an error

        Args:
            annotation: Type annotation to generate the schema for.
            serializer: Serializer that knows how to build
                a raw JSON schema from the annotation.
            used_for_response: Whether this schema describes a response,
                since some serializers generate different
                schemas for inputs and outputs.
            skip_registration: Do not register the resulting schema
                in the registry, return an inlined ``Schema``
                instead of a ``Reference``.
            register_referenced_components: Still register
                the nested components the schema refers to,
                even when ``skip_registration`` is set.
                Only makes sense together with ``skip_registration``.

        Raises:
            UnsolvableAnnotationsError: when we can't generate
                an OpenAPI schema from an existing annotation.

        """
        existing_reference = self._context.registries.schema.get_reference(
            (
                serializer.schema_generator.schema_name(annotation)
                or getattr(annotation, '__qualname__', None)
            ),
            annotation,
        )
        if existing_reference is not None:
            return existing_reference

        try:
            schemas = serializer.schema_generator.get_schema(
                annotation,
                ref_template=self._context.registries.schema.schema_prefix,
                used_for_response=used_for_response,
            )
        except Exception as exc:
            raise UnsolvableAnnotationsError(
                f'Cannot generate OpenAPI schema from {annotation}, '
                'consider registering it as described in your serializer',
            ) from exc
        return self._maybe_generate_reference(
            annotation,
            *schemas,
            serializer,
            skip_registration=skip_registration,
            register_referenced_components=register_referenced_components,
        )

    def _maybe_generate_reference(
        self,
        annotation: Any,
        schema: dict[str, Any],
        components: dict[str, Any],
        serializer: type['BaseSerializer'],
        *,
        skip_registration: bool,
        register_referenced_components: bool,
    ) -> Reference | Schema:
        reference = schema.get('$ref')  # FIXME: this can be a schema with $ref
        loaded_components = {
            component_name: load_schema(component)
            for component_name, component in components.items()
        }
        self._register_components(
            loaded_components,
            reference,
            skip_registration=skip_registration,
            register_referenced_components=register_referenced_components,
        )

        if reference:
            return self._resolve_reference(
                annotation,
                Reference(
                    ref=reference,
                    summary=schema.get('summary'),
                    description=schema.get('description'),
                ),
                loaded_components,
                serializer,
                skip_registration=skip_registration,
            )

        schema_obj = load_schema(schema)
        self._maybe_generate_example(schema_obj, annotation, serializer)
        if not skip_registration and schema_obj.title:
            return self._context.registries.schema.register(
                schema_name=schema_obj.title,
                schema=schema_obj,
                annotation=annotation,
            )
        return schema_obj

    def _register_components(
        self,
        components: dict[str, Schema],
        reference: str | None,
        *,
        skip_registration: bool,
        register_referenced_components: bool,
    ) -> None:
        """
        Register nested components of a schema.

        Components are registered when the schema itself is registered,
        or when explicitly asked for with ``register_referenced_components``.

        When the schema is a reference and its registration is skipped,
        the referenced component is inlined instead of being registered,
        while all other nested components are still registered.
        """
        if skip_registration and not register_referenced_components:
            return

        registry = self._context.registries.schema
        inlined_component = (
            reference.removeprefix(registry.schema_prefix)
            if skip_registration and reference
            else None
        )
        for component_name, component in components.items():
            if component_name != inlined_component:
                registry.register(component_name, component)

    def _resolve_reference(
        self,
        annotation: Any,
        reference: Reference,
        components: dict[str, Schema],
        serializer: type['BaseSerializer'],
        *,
        skip_registration: bool,
    ) -> Reference | Schema:
        registry = self._context.registries.schema
        if skip_registration:
            return registry.maybe_resolve_reference(
                reference,
                resolution_context=components,
            )
        # If we got a reference from the start,
        # it might still miss the examples:
        self._maybe_generate_example(
            registry.maybe_resolve_reference(reference),
            annotation,
            serializer,
        )
        return reference

    def _maybe_generate_example(
        self,
        schema: Schema,
        annotation: Any,
        serializer: type['BaseSerializer'],
    ) -> None:
        if not schema.example and not schema.examples:  # pragma: no branch
            set_generated_example(
                schema,
                generate_example(annotation, serializer),
            )
