from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True, slots=True)
class BaseObject:
    """Base class for schema spec objects."""
