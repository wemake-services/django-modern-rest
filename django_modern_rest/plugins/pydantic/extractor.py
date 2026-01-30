from dataclasses import fields
from typing import Any, cast

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from typing_extensions import override

from django_modern_rest.openapi.extractors.base import BaseFieldExtractor
from django_modern_rest.openapi.types import FieldDefinition, KwargDefinition


class PydanticFieldExtractor(BaseFieldExtractor[type[BaseModel]]):
    """Extract field definitions from Pydantic models."""

    @classmethod
    @override
    def is_supported(cls, source: Any) -> bool:
        """Check if the source is a Pydantic model."""
        return isinstance(source, type) and issubclass(
            source,
            BaseModel,
        )

    @override
    def extract_fields(
        self,
        source: type[BaseModel],
    ) -> list[FieldDefinition]:
        """
        Extract fields from a Pydantic model.

        Args:
            source: A Pydantic BaseModel subclass.

        Returns:
            A list of FieldDefinition objects.
        """
        definitions: list[FieldDefinition] = []

        for name, field_info in source.model_fields.items():
            definitions.append(
                self._create_field_definition(name, field_info),
            )

        return definitions

    def _create_field_definition(
        self,
        name: str,
        field_info: FieldInfo,
    ) -> FieldDefinition:
        kwarg_definition = self._create_kwarg_definition(field_info)

        default = field_info.default
        if default == PydanticUndefined:
            default = None

        return FieldDefinition(
            name=name,
            annotation=field_info.annotation,
            default=default,
            kwarg_definition=kwarg_definition,
            extra_data={
                'alias': field_info.alias,
                'is_required': field_info.is_required(),
            },
        )

    def _create_kwarg_definition(
        self,
        field_info: FieldInfo,
    ) -> KwargDefinition:
        kwargs: dict[str, Any] = {}
        for kwarg_field in fields(KwargDefinition):
            kwarg_value = getattr(field_info, kwarg_field.name, None)

            if kwarg_value is None:
                kwarg_value = self._get_from_metadata(
                    field_info,
                    kwarg_field.name,
                )

            if kwarg_value is not None:
                if kwarg_value == PydanticUndefined:
                    kwarg_value = None
                kwargs[kwarg_field.name] = kwarg_value

        if field_info.json_schema_extra:
            kwargs['schema_extra'] = cast(
                dict[str, Any],
                field_info.json_schema_extra,
            )

        return KwargDefinition(**kwargs)

    def _get_from_metadata(
        self,
        field_info: FieldInfo,
        name: str,
    ) -> Any:
        for metadata_item in field_info.metadata:
            metadata_value = getattr(metadata_item, name, None)
            if metadata_value is not None:
                return metadata_value
        return None
