from dataclasses import dataclass


@dataclass
class OpenAPIConfig:
    """Configuration for OpenAPI."""

    title: str
    version: str
