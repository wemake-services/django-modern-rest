from typing import TYPE_CHECKING, Any, ClassVar

import pydantic
from django.utils.module_loading import import_string
from typing_extensions import override

from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    DMR_JSON_DESERIALIZE_KEY,
    DMR_JSON_SERIALIZE_KEY,
    resolve_defaults,
)

if TYPE_CHECKING:
    from django_modern_rest.internal.json import (
        Deserialize,
        FromJson,
        Serialize,
    )


class PydanticSerializer(BaseSerializer):
    _serialize: ClassVar['Serialize']
    _deserialize: ClassVar['Deserialize']
    _strict: ClassVar[bool] = True

    __slots__ = ()

    # TODO: use `TypedDict`
    model_dump_kwargs: ClassVar[dict[str, Any]] = {
        'by_alias': True,
        'mode': 'json',
    }

    @override
    @classmethod
    def to_json(cls, structure: Any) -> bytes:
        return cls._get_serialize_func()(structure, cls.serialize_hook)

    @override
    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        if isinstance(to_serialize, pydantic.BaseModel):
            return to_serialize.model_dump(**cls.model_dump_kwargs)
        return super().serialize_hook(to_serialize)

    @override
    @classmethod
    def from_json(cls, buffer: 'FromJson') -> Any:
        return cls._get_deserialize_func()(
            buffer,
            cls.deserialize_hook,
            strict=cls._strict,
        )

    @override
    @classmethod
    def from_python(
        cls,
        unstructured: Any,
        model: Any,
        # TODO: use a TypedDict
        from_python_kwargs: dict[str, Any],
    ) -> Any:
        return pydantic.TypeAdapter(model).validate_python(
            unstructured,
            **from_python_kwargs,
        )

    @override
    @classmethod
    def deserialize_hook(
        cls,
        target_type: type[Any],
        to_deserialize: Any,
    ) -> Any:
        # TODO: implement custom `pydantic` fields support
        return super().deserialize_hook(target_type, to_deserialize)

    # TODO: merge `_get_serialize_func` and `_get_deserialize_func`?
    @classmethod
    def _get_serialize_func(cls) -> 'Serialize':
        existing_attr: Serialize | None = getattr(cls, '_serialize', None)
        if existing_attr is not None:
            return existing_attr

        setting = resolve_defaults()[DMR_JSON_SERIALIZE_KEY]
        cls._serialize = (
            import_string(setting) if isinstance(setting, str) else setting
        )
        return cls._serialize

    @classmethod
    def _get_deserialize_func(cls) -> 'Deserialize':
        existing_attr: Deserialize | None = getattr(cls, '_deserialize', None)
        if existing_attr is not None:
            return existing_attr

        setting = resolve_defaults()[DMR_JSON_DESERIALIZE_KEY]
        cls._deserialize = (
            import_string(setting) if isinstance(setting, str) else setting
        )
        return cls._deserialize
