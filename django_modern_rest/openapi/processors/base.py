import abc


class BaseProcessor:
    """Whatever must be replaced."""

    @abc.abstractmethod
    def is_supports(self) -> bool:
        """Whatever must be replaced."""
        raise NotImplementedError

    @abc.abstractmethod
    def process(self) -> ...:
        """Whatever must be replaced."""
        raise NotImplementedError
