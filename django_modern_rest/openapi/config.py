from dataclasses import dataclass, field

from django_modern_rest.openapi.components import Contact, License


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
