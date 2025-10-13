from dataclasses import dataclass, field


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
class OpenAPIConfig:
    """Configuration for OpenAPI."""

    title: str
    version: str

    summary: str | None = None
    description: str | None = None
    terms_of_service: str | None = field(
        default=None,
        metadata={'alias': 'termsOfService'},
    )
    contact: Contact | None = None
    license: License | None = None


# TODO: add
# servers,
# paths,
# webhooks,
# components,
# security,
# tags,
# externalDocs
