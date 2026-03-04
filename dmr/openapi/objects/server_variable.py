from dataclasses import dataclass


@dataclass(kw_only=True)
class ServerVariable:
    """An object representing a `Server Variable` for server URL template."""

    default: str
    enum: list[str] | None = None
    description: str | None = None
