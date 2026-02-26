# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/_openapi/schema_generation/schema.py
# under MIT license.

# Original license:
# https://github.com/litestar-org/litestar/blob/main/LICENSE

# The MIT License (MIT)

# Copyright (c) 2021, 2022, 2023, 2024, 2025, 2026 Litestar Org.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import dataclasses
from collections.abc import Mapping, Sequence
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Union,
    get_args,
    get_origin,
)

from typing_extensions import is_typeddict

from dmr.internal.schema import get_schema_name
from dmr.openapi.extractors.finder import find_extractor
from dmr.openapi.mappers import TypeMapper
from dmr.openapi.objects.enums import OpenAPIType
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.schema import Schema
from dmr.openapi.types import FieldDefinition, KwargDefinition

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.mappers import KwargMapper


@dataclasses.dataclass(frozen=True, slots=True)
class SchemaGenerator:
    """Generate ``FieldDefinition`` from dtos."""

    _context: 'OpenAPIContext'

    def __call__(self, annotation: Any) -> Schema | Reference:
        """Get schema for a type."""
        simple_schema = TypeMapper.get_schema(
            annotation,
        ) or self._context.registries.schema.get_reference(annotation)
        if simple_schema:
            return simple_schema

        origin = get_origin(annotation) or annotation

        if origin is Annotated:
            return self(get_args(annotation)[0])

        generic_schema = _handle_generic_types(
            self,
            origin,
            get_args(annotation),
        )
        if generic_schema:
            return generic_schema

        return self._generate_reference(annotation)

    def _generate_reference(self, source_type: Any) -> Reference:
        extractor = find_extractor(source_type)
        props, required = self._extract_properties(
            extractor.extract_fields(source_type),
            extractor.mapper_cls(),
        )

        return self._context.registries.schema.register(
            source_type=source_type,
            schema=Schema(
                type=OpenAPIType.OBJECT,
                properties=props,
                required=required or None,
            ),
            name=get_schema_name(source_type),
        )

    def _extract_properties(
        self,
        field_definitions: list[FieldDefinition],
        mapper: 'KwargMapper',
    ) -> tuple[dict[str, Schema | Reference], list[str]]:
        props: dict[str, Schema | Reference] = {}
        required: list[str] = []

        for field_definition in field_definitions:
            schema = self(field_definition.annotation)

            if field_definition.kwarg_definition:
                schema = self._apply_kwarg_definition(
                    schema,
                    field_definition.kwarg_definition,
                    mapper,
                )

            props[field_definition.name] = schema

            if field_definition.extra_data.get('is_required'):
                required.append(field_definition.name)
        return props, required

    def _apply_kwarg_definition(
        self,
        schema: Schema | Reference,
        kwarg_definition: KwargDefinition,
        mapper: 'KwargMapper',
    ) -> Schema | Reference:
        if isinstance(schema, Reference):
            # TODO: handle Reference wrapping with allOf?
            return schema

        updates = mapper(schema, kwarg_definition)

        if not updates:
            return schema

        return dataclasses.replace(schema, **updates)


def _handle_generic_types(
    generator: SchemaGenerator,
    origin: Any,
    args: tuple[Any, ...],
) -> Schema | Reference | None:
    if is_typeddict(origin):
        return None

    if origin is UnionType or origin is Union:
        return _handle_union(generator, args)

    if isinstance(origin, type) and issubclass(origin, Mapping):
        return _handle_mapping(generator, args)

    if (
        isinstance(origin, type)
        and issubclass(origin, Sequence)
        and origin not in {str, bytes, bytearray}
    ):
        return _handle_sequence(generator, args)

    return None


def _handle_union(
    generator: SchemaGenerator,
    args: tuple[Any, ...],
) -> Schema | Reference:
    is_nullable = any(arg in {NoneType, type(None)} for arg in args)
    real_args = [arg for arg in args if arg not in {NoneType, type(None)}]

    if not real_args:
        # We know that NoneType is registered in TypeMapper
        return TypeMapper.get_schema(NoneType)  # type: ignore[return-value]

    if len(real_args) == 1:
        schema = generator(real_args[0])
        if is_nullable:
            return Schema(one_of=[schema, Schema(type=OpenAPIType.NULL)])
        return schema

    schemas: list[Schema | Reference] = [generator(arg) for arg in real_args]
    if is_nullable:
        schemas.append(Schema(type=OpenAPIType.NULL))

    return Schema(one_of=schemas)


def _handle_mapping(
    generator: SchemaGenerator,
    args: tuple[Any, ...],
) -> Schema:
    value_type = args[1] if len(args) >= 2 else Any
    return Schema(
        type=OpenAPIType.OBJECT,
        additional_properties=generator(value_type),
    )


def _handle_sequence(
    generator: SchemaGenerator,
    args: tuple[Any, ...],
) -> Schema:
    items_schema = None
    if args:
        items_schema = generator(args[0])
    return Schema(type=OpenAPIType.ARRAY, items=items_schema)
