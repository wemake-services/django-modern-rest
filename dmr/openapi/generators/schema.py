import dataclasses
from typing import TYPE_CHECKING, Any

from dmr.exceptions import UnsolvableAnnotationsError
from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.schema import Schema

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True)
class SchemaGenerator:
    """Generate OpenAPI schemas from different type annotations."""

    # Instance API:
    _context: 'OpenAPIContext'

    def __call__(
        self,
        annotation: Any,
        serializer: type['BaseSerializer'],
        *,
        used_for_response: bool = False,
        fake_schema: bool = False,
    ) -> Schema | Reference:
        """
        Get schema for an annotation.

        Here's the algorithm we use:
        1. First we try to find any existing schema references
        2. Next, we try to get a model schema from a serializer.
           If it exists, we create an internal reference and return it.
           The next time it will returned as a reference, cached.
        3. If nothing worked, we raise an error

        Raises:
            UnsolvableAnnotationsError: when we can't generate
                an OpenAPI schema from an existing annotation.

        """
        existing_reference = self._context.registries.schema.get_reference(
            # TODO: fix this, schema name generation must be strandartized
            getattr(annotation, '__qualname__', None),
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
                *schemas,
                fake_schema=fake_schema,
            )
        raise UnsolvableAnnotationsError(
            f'Cannot generate OpenAPI schema from {annotation}, '
            'consider registerting it as described in your serializer',
        )

    def _maybe_generate_reference(
        self,
        schema: dict[str, Any],
        components: dict[str, Any],
        *,
        fake_schema: bool,
    ) -> Schema | Reference:
        if not fake_schema:
            for component_name, component in components.items():
                self._context.registries.schema.register(
                    schema_name=component_name,
                    schema=load_schema(component),
                )

        reference = schema.get('$ref')
        if reference:
            # We got a reference back, return it. It is registered already.
            return Reference(
                ref=reference,
                summary=schema.get('summary'),
                description=schema.get('description'),
            )

        # Register the final schema:
        schema_obj = load_schema(schema)
        if schema_obj.title and not fake_schema:
            return self._context.registries.schema.register(
                schema_name=schema_obj.title,
                schema=schema_obj,
            )
        return schema_obj
