from dataclasses import fields
from typing import Any, cast

from typing_extensions import override

from django_modern_rest.openapi.extractors.base import BaseFieldExtractor
from django_modern_rest.openapi.types import FieldDefinition, KwargDefinition

try:
    import pydantic
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pydantic` is not installed, '
        "consider using `pip install 'django-modern-rest[pydantic]'`",
    )
    raise

import pydantic_core


class PydanticFieldExtractor(BaseFieldExtractor['type[pydantic.BaseModel]']):
    """Extract field definitions from Pydantic models."""

    @classmethod
    @override
    def is_supported(cls, source: Any) -> bool:
        """Check if the source is a Pydantic model."""
        if not isinstance(source, type):
            return False
        return issubclass(source, pydantic.BaseModel)

    @override
    def extract_fields(
        self,
        source: 'type[pydantic.BaseModel]',
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
        field_info: 'pydantic.fields.FieldInfo',
    ) -> FieldDefinition:
        kwarg_definition = self._create_kwarg_definition(field_info)

        default = field_info.default
        if default == pydantic_core.PydanticUndefined:
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
        field_info: 'pydantic.fields.FieldInfo',
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
                if kwarg_value == pydantic_core.PydanticUndefined:
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
        field_info: 'pydantic.fields.FieldInfo',
        name: str,
    ) -> Any:
        for metadata_item in field_info.metadata:
            metadata_value = getattr(metadata_item, name, None)
            if metadata_value is not None:
                return metadata_value
        return None
