from typing import TYPE_CHECKING, Any, ClassVar

try:
    import pydantic
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pydantic` is not installed, '
        "consider using `pip install 'django-modern-rest[pydantic]'`",
    )
    raise

from django.utils.module_loading import import_string
from typing_extensions import override

from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    DMR_DESERIALIZE_KEY,
    DMR_SERIALIZE_KEY,
    resolve_setting,
)

if TYPE_CHECKING:
    from django_modern_rest.internal.json import (
        Deserialize,
        FromJson,
        Serialize,
    )


class PydanticSerializer(BaseSerializer):
    __slots__ = ()

    # Required API:
    validation_error: ClassVar[type[Exception]] = pydantic.ValidationError

    # Custom API:

    # TODO: use `TypedDict`
    model_dump_kwargs: ClassVar[dict[str, Any]] = {
        'by_alias': True,
        'mode': 'json',
    }
    # TODO: use a TypedDict
    from_python_kwargs: ClassVar[dict[str, Any]] = {
        'by_alias': True,
    }
    from_json_strict: ClassVar[bool] = True

    # Private API:

    _serialize: ClassVar['Serialize']
    _deserialize: ClassVar['Deserialize']

    @override
    @classmethod
    def to_json(cls, structure: Any) -> bytes:
        return _get_serialize_func(cls)(structure, cls.serialize_hook)

    @override
    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        if isinstance(to_serialize, pydantic.BaseModel):
            return to_serialize.model_dump(**cls.model_dump_kwargs)
        return super().serialize_hook(to_serialize)

    @override
    @classmethod
    def from_json(cls, buffer: 'FromJson') -> Any:
        return _get_deserialize_func(cls)(
            buffer,
            cls.deserialize_hook,
            strict=cls.from_json_strict,
        )

    @override
    @classmethod
    def from_python(
        cls,
        unstructured: Any,
        model: Any,
    ) -> Any:
        return pydantic.TypeAdapter(model).validate_python(
            unstructured,
            **cls.from_python_kwargs,
        )

    @override
    @classmethod
    def deserialize_hook(
        cls,
        target_type: type[Any],
        to_deserialize: Any,
    ) -> Any:
        # TODO: provide docs why this is needed
        return super().deserialize_hook(target_type, to_deserialize)


# TODO: merge `_get_serialize_func` and `_get_deserialize_func`?
def _get_serialize_func(cls: type[PydanticSerializer]) -> 'Serialize':
    existing_attr: Serialize | None = getattr(cls, '_serialize', None)
    if existing_attr is not None:
        return existing_attr

    setting = resolve_setting(DMR_SERIALIZE_KEY)
    cls._serialize = (  # pyright: ignore[reportPrivateUsage]
        import_string(setting) if isinstance(setting, str) else setting
    )
    return cls._serialize  # pyright: ignore[reportPrivateUsage]


def _get_deserialize_func(cls: type[PydanticSerializer]) -> 'Deserialize':
    existing_attr: Deserialize | None = getattr(cls, '_deserialize', None)
    if existing_attr is not None:
        return existing_attr

    setting = resolve_setting(DMR_DESERIALIZE_KEY)
    cls._deserialize = (  # pyright: ignore[reportPrivateUsage]
        import_string(setting) if isinstance(setting, str) else setting
    )
    return cls._deserialize  # pyright: ignore[reportPrivateUsage]
