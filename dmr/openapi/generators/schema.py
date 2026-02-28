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
from typing import TYPE_CHECKING, Any, ClassVar

from dmr.internal.schema import get_schema_name
from dmr.openapi.extractors.finder import find_extractor
from dmr.openapi.mappers.types import TypeMapper
from dmr.openapi.objects.enums import OpenAPIType
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.schema import Schema
from dmr.openapi.types import FieldDefinition, KwargDefinition

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.mappers.kwargs import KwargMapper


@dataclasses.dataclass(frozen=True, slots=True)
class SchemaGenerator:
    """Generate ``FieldDefinition`` from dtos."""

    type_mapper: ClassVar[type[TypeMapper]] = TypeMapper
    _context: 'OpenAPIContext'

    def __call__(self, annotation: Any) -> Schema | Reference:
        """Get schema for a type."""
        primitive_schema = self.type_mapper.get_schema(
            annotation,
            self,
        )
        if primitive_schema:
            return primitive_schema
        existing_reference = self._context.registries.schema.get_reference(
            annotation,
        )
        if existing_reference:
            return existing_reference
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
