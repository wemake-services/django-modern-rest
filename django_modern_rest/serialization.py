import abc
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

if TYPE_CHECKING:
    from django_modern_rest.internal.json import FromJson

_ModelT = TypeVar('_ModelT')


class BaseSerializer:
    """Abstract base class for JSON serialization."""

    content_type: ClassVar[str] = 'application/json'

    __slots__ = ()

    @classmethod
    @abc.abstractmethod
    def to_json(cls, structure: Any) -> bytes:
        raise NotImplementedError

    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        raise TypeError(
            f'Value {to_serialize} of type {type(to_serialize)} '
            'is not supported',
        )

    @classmethod
    @abc.abstractmethod
    def from_json(cls, buffer: 'FromJson') -> Any:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def from_python(
        cls,
        unstructured: Any,
        model: Any,
        from_python_kwargs: dict[str, Any],
    ) -> Any:
        raise NotImplementedError

    @classmethod
    def deserialize_hook(
        cls,
        target_type: type[Any],
        to_deserialize: Any,
    ) -> Any:
        raise TypeError(
            f'Value {to_deserialize} of type {type(to_deserialize)} '
            f'is not supported for {target_type}',
        )
