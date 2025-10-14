from dataclasses import dataclass


@dataclass
class Contact:
    """Contact for the OpenAPI."""

    name: str | None = None
    url: str | None = None
    email: str | None = None


@dataclass
class License:
    """License for the OpenAPI."""

    name: str
    identifier: str | None = None
    url: str | None = None


@dataclass
class ServerVariable:
    """Server variable for the OpenAPI."""

    default: str
    enum: list[str] | None = None
    description: str | None = None


@dataclass
class Servers:
    """Servers for the OpenAPI."""

    url: str
    description: str | None = None
    variables: dict[str, ServerVariable] | None = None


# TODO: add
# paths,
# webhooks,
# components,
# security,
# tags,
# externalDocs
