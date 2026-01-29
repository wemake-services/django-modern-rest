from abc import abstractmethod
from typing import Any, Generic, TypeVar

from django_modern_rest.openapi.types import FieldDefinition

_SourceT = TypeVar('_SourceT')


class BaseFieldExtractor(Generic[_SourceT]):
    """Base class for field definitions extractors."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def is_supported(cls, source: Any) -> bool:
        """Check if the extractor supports the given source."""
        raise NotImplementedError

    @abstractmethod
    def extract_fields(self, source: _SourceT) -> list[FieldDefinition]:
        """Retrieves a field definitions from a dto."""
        raise NotImplementedError
