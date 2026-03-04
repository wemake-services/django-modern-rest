from dataclasses import dataclass


@dataclass(kw_only=True)
class ExternalDocumentation:
    """Allows referencing an external resource for extended documentation."""

    url: str
    description: str | None = None
