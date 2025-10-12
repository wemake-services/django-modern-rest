from collections.abc import Callable
from typing import Any, ClassVar, TypeAlias

import pydantic
from django.utils.module_loading import import_string

from django_modern_rest.controller import RestEndpoint
from django_modern_rest.serialization import BaseSerializer, FromJson
from django_modern_rest.settings import (
    DMR_JSON_DESERIALIZER_KEY,
    DMR_JSON_SERIALIZER_KEY,
    resolve_defaults,
)

_SerializeHook: TypeAlias = Callable[[Any], Any]
_Serialize: TypeAlias = Callable[[Any, _SerializeHook], str]


_Deserialize: TypeAlias = Callable[[FromJson], Any]


class PydanticSerializer(BaseSerializer):
    """Pydantic-based JSON serializer for REST endpoints."""

    _serialize: ClassVar[_Serialize]
    _deserialize: ClassVar[_Deserialize]

    @classmethod
    def to_json(cls, structure: Any) -> str:
        """Serialize structure to JSON using pydantic serializer."""
        return cls._serialize()(structure, cls.serialization_hook)

    @classmethod
    def serialization_hook(cls, to_serialize: Any) -> Any:
        """Hook for custom serialization of pydantic fields."""
        # TODO: implement custom `pydantic` fields support
        return super().serialization_hook(to_serialize)

    @classmethod
    def from_json(cls, buffer: FromJson) -> Any:
        """Deserialize JSON buffer using pydantic deserializer."""
        return cls._deserialize()(buffer)

    # TODO: merge `_serialize` and `_deserialize`?
    @classmethod
    def _serialize(cls) -> _Serialize:
        existing_attr = getattr(cls, '_serialize', None)
        if existing_attr is not None:
            return existing_attr

        setting = cls._setting_name(DMR_JSON_SERIALIZER_KEY)
        cls._serialize = (
            import_string(setting) if isinstance(setting, str) else setting
        )
        return cls._serialize

    @classmethod
    def _deserialize(cls) -> _Deserialize:
        existing_attr = getattr(cls, '_deserialize', None)
        if existing_attr is not None:
            return existing_attr

        setting = cls._setting_name(DMR_JSON_DESERIALIZER_KEY)
        cls._deserialize = (
            import_string(setting) if isinstance(setting, str) else setting
        )
        return cls._deserialize

    @classmethod
    def _setting_name(cls, suffix: str) -> str:
        return resolve_defaults().get(suffix)


def rest(
    *,
    return_dto: type[pydantic.BaseModel],
) -> type[RestEndpoint]:
    """
    Decorator for REST endpoints.

    When *return_dto* is passed, it means that we return
    an instance of :class:`django.http.HttpResponse` or its subclass.
    But, we still want to show the response type in OpenAPI schema
    and also want to do an extra round of validation
    to be sure that it fits the schema.
    """

    def decorator(func):
        func.__metadata__ = {'return_dto': return_dto}
        return func

    return decorator
