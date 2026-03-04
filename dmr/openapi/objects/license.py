from dataclasses import dataclass


@dataclass(kw_only=True)
class License:
    """License information for the exposed API."""

    name: str
    identifier: str | None = None
    url: str | None = None
