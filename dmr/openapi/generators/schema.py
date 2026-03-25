import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    get_args,
    get_origin,
    overload,
)

from dmr.exceptions import UnsolvableAnnotationsError
from dmr.openapi.mappers.example import generate_example
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
    ) -> Schema: ...

    @overload
    def __call__(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        *,
        used_for_response: bool = False,
        skip_registration: bool = False,
    ) -> Schema | Reference: ...

    def __call__(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        *,
        used_for_response: bool = False,
        skip_registration: bool = False,
    ) -> Schema | Reference:
        """
        Get schema for an annotation.

        Here's the algorithm we use:

        1. First, we try to find manually defined overrides for the annotation
        2. If nothing is found, we try to find any existing schema references
        3. Next, we try to get a model schema from a serializer.
           If it exists, we create an internal reference and return it.
           The next time it will returned as a reference, cached.
        4. If nothing worked, we raise an error

        Raises:
            UnsolvableAnnotationsError: when we can't generate
                an OpenAPI schema from an existing annotation.

        """
        explicit_override = self._resolve_schema_override(
            annotation,
            serializer,
            used_for_response=used_for_response,
            skip_registration=skip_registration,
        )
        if explicit_override:
            return explicit_override

        existing_reference = self._context.registries.schema.get_reference(
            (
                serializer.schema_generator.schema_name(annotation)
                or getattr(annotation, '__qualname__', None)
            ),
            annotation,
        )
        if existing_reference is not None:
            return existing_reference

        schemas = serializer.schema_generator.get_schema(
            annotation,
            ref_template=self._context.registries.schema.schema_prefix,
            used_for_response=used_for_response,
        )
        if schemas is not None:
            return self._maybe_generate_reference(
                annotation,
                *schemas,
                serializer,
                skip_registration=skip_registration,
            )
        raise UnsolvableAnnotationsError(
            f'Cannot generate OpenAPI schema from {annotation}, '
            'consider registerting it as described in your serializer',
        )

    def _resolve_schema_override(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        *,
        used_for_response: bool = False,
        skip_registration: bool = False,
    ) -> Schema | Reference | None:
        origin = get_origin(annotation) or annotation
        type_args = get_args(annotation)

        registry = self._context.registries.schema
        schema = registry.overrides.get(origin)
        if callable(schema):
            return schema(
                annotation,
                origin,
                type_args,
                used_for_response=used_for_response,
                skip_registration=skip_registration,
            )
        if schema is not None:
            return schema
        return None

    def _maybe_generate_reference(
        self,
        annotation: Any,
        schema: dict[str, Any],
        components: dict[str, Any],
        serializer: type['BaseSerializer'],
        *,
        skip_registration: bool = False,
    ) -> Schema | Reference:
        if not skip_registration:
            for component_name, component in components.items():
                self._context.registries.schema.register(
                    schema_name=component_name,
                    schema=load_schema(component),
                )

        reference = schema.get('$ref')
        if reference:
            # We got a reference back, return it. It is registered already.
            reference = Reference(
                ref=reference,
                summary=schema.get('summary'),
                description=schema.get('description'),
            )
            if not skip_registration:
                # If we got a reference from the start,
                # it might still miss the examples:
                self._maybe_generate_example(reference, annotation, serializer)

            # When we create skip registration, we need
            # real schemas back, not references,
            # because there's no registered schema under the reference.
            return (
                self._context.registries.schema.maybe_resolve_reference(
                    reference,
                    resoltion_context=_build_resolution_context(components),
                )
                if skip_registration
                else reference
            )

        # Register the final schema:
        schema_obj = load_schema(
            schema,
            should_generate_example=True,
            annotation=annotation,
            serializer=serializer,
        )
        if not skip_registration and schema_obj.title:
            return self._context.registries.schema.register(
                schema_name=schema_obj.title,
                schema=schema_obj,
                annotation=annotation,
            )
        return schema_obj

    def _maybe_generate_example(
        self,
        reference: Reference,
        annotation: Any,
        serializer: type['BaseSerializer'],
    ) -> None:
        schema = self._context.registries.schema.maybe_resolve_reference(
            reference,
        )
        if not schema.example and not schema.examples:  # pragma: no branch
            schema.example = generate_example(annotation, serializer)


def _build_resolution_context(
    components: dict[str, Any],
) -> dict[str, Schema]:
    return {
        component_name: load_schema(component)
        for component_name, component in components.items()
    }
