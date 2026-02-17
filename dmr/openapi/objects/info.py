from dataclasses import dataclass
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.contact import Contact
    from django_modern_rest.openapi.objects.license import License


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Info:
    """
    The Info object provides metadata about the API.

    The metadata MAY be used by the clients if needed, and MAY be presented
    in editing or documentation generation tools for convenience.
    """

    title: str
    version: str
    summary: str | None = None
    description: str | None = None
    terms_of_service: str | None = None
    contact: 'Contact | None' = None
    license: 'License | None' = None
