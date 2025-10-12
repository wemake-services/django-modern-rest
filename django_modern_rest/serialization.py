import abc
from typing import Any, ClassVar, Generic, TypeAlias, TypeVar

from django.http import HttpRequest

_ModelT = TypeVar('_ModelT')

#: Types that are possible to load json from.
FromJson: TypeAlias = str | bytes | bytearray


class BaseSerializer:
    """Abstract base class for JSON serialization."""

    content_type: ClassVar[str] = 'application/json'

    @classmethod
    @abc.abstractmethod
    def to_json(cls, structure: Any) -> str:
        """Serialize structure to JSON string."""
        raise NotImplementedError

    @classmethod
    def serialization_hook(cls, to_serialize: Any) -> Any:
        """Hook for custom serialization of special types."""
        # TODO: implement default fields support, like `UUID`
        return to_serialize

    @classmethod
    @abc.abstractmethod
    def from_json(cls, buffer: FromJson) -> Any:
        """Deserialize JSON buffer to Python object."""
        raise NotImplementedError


class ComponentParserMixin(Generic[_ModelT]):
    """Base abtract parser for request components."""

    __is_base_type__: ClassVar[bool] = True

    # We lie that it is an isntance attribute, but
    # we can't use type vars in class attrs.
    __model__: type[_ModelT]

    @abc.abstractmethod
    def _parse_component(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        raise NotImplementedError
