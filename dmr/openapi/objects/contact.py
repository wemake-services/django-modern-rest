from dataclasses import dataclass


@dataclass(kw_only=True)
class Contact:
    """Contact information for the exposed API."""

    name: str | None = None
    url: str | None = None
    email: str | None = None
