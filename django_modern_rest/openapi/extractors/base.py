from abc import abstractmethod
from typing import Any, ClassVar, Generic, TypeAlias, TypeVar

from typing_extensions import override

from django_modern_rest.openapi.types import FieldDefinition

_SourceT = TypeVar('_SourceT')
_Registry: TypeAlias = list['type[FieldExtractor[Any]]']


class FieldExtractor(Generic[_SourceT]):
    """Base class for field definitions extractors."""

    __slots__ = ()

    registry: ClassVar[_Registry] = []

    @override
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.registry.append(cls)

    @classmethod
    @abstractmethod
    def is_supported(cls, source: Any) -> bool:
        """Check if the extractor supports the given source."""
        raise NotImplementedError

    @abstractmethod
    def extract_fields(self, source: _SourceT) -> list[FieldDefinition]:
        """Retrieves a field definitions from a dto."""
        raise NotImplementedError
