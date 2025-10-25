import abc
from typing import Any


class BaseProcessor:
    """Whatever must be replaced."""

    @abc.abstractmethod
    def is_supports(self) -> bool:
        """Whatever must be replaced."""
        raise NotImplementedError

    @abc.abstractmethod
    def process(self) -> Any:
        """Whatever must be replaced."""
        raise NotImplementedError
