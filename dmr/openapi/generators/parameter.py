import dataclasses
from typing import TYPE_CHECKING, Any

from dmr.openapi.objects import (
    Parameter,
    ParameterLocation,
    ParameterMetadata,
    Reference,
    Schema,
)

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.metadata import EndpointMetadata
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.generators.schema import LoadedSchema
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True)
class ParameterGenerator:
    """Generator for OpenAPI ``Parameter`` objects."""

    _context: 'OpenAPIContext'

    def __call__(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
        *,
        param_in: ParameterLocation,
    ) -> list[Parameter | Reference]:
        """
        Generate parameter spec for the OpenAPI.

        Parameters are generated from the properties of object schemas.
        Unions like ``Query[Model | None] = None``
        or ``Query[Model | Literal['']] = ''`` are supported:
        only their object members have properties, other members
        can only come from defaults, not from the request.
        When there are several object members, a parameter is required
        only when it is required by all of them.

        .. versionchanged:: 0.16.0
            Now accepts *metadata* and *controller_cls* parameters.
            Removed *serializer* and *context* parameters.
            Union models are now supported.

        """
        # Import cycle:
        from dmr.metadata import get_annotated_metadata  # noqa: PLC0415

        loaded = self._context.generators.schema.load(
            model,
            controller_cls.serializer,
            inline=True,
        )
        generated = self._generate(
            loaded,
            get_annotated_metadata(
                model,
                ParameterMetadata,
                model_meta=model_meta,
            ),
            param_in=param_in,
        )
        # Models themselves are inlined as parameters, only components
        # used by their properties are needed in the schema:
        self._context.generators.schema.register(generated, loaded)
        return generated

    def _generate(
        self,
        loaded: 'LoadedSchema',
        annotated_meta: ParameterMetadata | None,
        *,
        param_in: ParameterLocation,
    ) -> list[Parameter | Reference]:
        object_schemas = self._object_schemas(loaded.schema, loaded.defs)
        return [  # pyright: ignore[reportReturnType]
            Parameter(
                name=property_name,
                param_in=param_in,
                schema=property_schema,
                # OpenAPI requires all path parameters to be required.
                # But, path fields can still have defaults, because
                # a controller can be routed to several urls,
                # and not all of them might have this parameter:
                required=(
                    param_in == 'path'
                    or all(
                        property_name in object_schema.required
                        for object_schema in object_schemas
                    )
                    or None
                ),
                **self._compute_metadata(
                    annotated_meta,
                    property_name,
                    property_schema,
                    object_schema,
                    loaded.defs,
                ),
            )
            for object_schema in object_schemas
            for property_name, property_schema in self._new_properties(
                object_schema,
                object_schemas,
            ).items()
        ]

    def _object_schemas(
        self,
        schema: Schema,
        defs: dict[str, Schema],
    ) -> list[Schema]:
        """
        Find all schemas with properties inside a schema.

        Unions are represented with ``anyOf`` or ``oneOf``,
        we look into their members recursively.
        """
        schema = self._context.registries.schema.maybe_resolve_reference(
            schema,
            resolution_context=defs,
        )
        members = schema.any_of or schema.one_of
        if not members:
            return [schema] if schema.properties else []
        object_schemas: list[Schema] = []
        for member in members:
            object_schemas.extend(self._object_schemas(member, defs))
        return object_schemas

    def _new_properties(
        self,
        object_schema: Schema,
        object_schemas: list[Schema],
    ) -> dict[str, Schema]:
        """Properties of *object_schema* that previous schemas don't have."""
        previous = object_schemas[: object_schemas.index(object_schema)]
        return {
            property_name: property_schema
            for property_name, property_schema in (
                object_schema.properties or {}
            ).items()
            if not any(
                property_name in (schema.properties or {})
                for schema in previous
            )
        }

    def _compute_metadata(
        self,
        annotated_meta: ParameterMetadata | None,
        property_name: str,
        property_schema: Schema,
        schema: Schema,
        defs: dict[str, Schema],
    ) -> dict[str, Any]:
        metadata_params = (
            {}
            if annotated_meta is None
            else {
                field.name: getattr(annotated_meta, field.name)
                for field in dataclasses.fields(annotated_meta)
            }
        )
        property_schema = (
            self._context.registries.schema.maybe_resolve_reference(
                property_schema,
                resolution_context=defs,
            )
        )
        return {
            **metadata_params,
            'description': (
                property_schema.description
                or metadata_params.get('description')
                or schema.description
            ),
            'deprecated': (
                property_schema.deprecated
                or metadata_params.get('deprecated')
                or schema.deprecated
                or None
            ),
        }
