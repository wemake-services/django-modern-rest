from dataclasses import dataclass

from django_modern_rest.openapi.objects.base import BaseObject


@dataclass(frozen=True, kw_only=True, slots=True)
class OAuthFlow(BaseObject):
    """TODO: add docs."""

    authorization_url: str | None = None
    token_url: str | None = None
    refresh_url: str | None = None
    scopes: dict[str, str] | None = None
