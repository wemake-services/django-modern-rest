from dataclasses import dataclass
from typing import final

from django_modern_rest.openapi.objects.base import BaseObject


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class OAuthFlow(BaseObject):
    """Configuration details for a supported OAuth Flow."""

    authorization_url: str | None = None
    token_url: str | None = None
    refresh_url: str | None = None
    scopes: dict[str, str] | None = None
