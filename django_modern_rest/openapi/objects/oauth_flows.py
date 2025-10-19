from dataclasses import dataclass
from typing import TYPE_CHECKING, final

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.oauth_flow import OAuthFlow


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class OAuthFlows(BaseObject):
    """Allows configuration of the supported OAuth Flows."""

    implicit: 'OAuthFlow | None' = None
    password: 'OAuthFlow | None' = None
    client_credentials: 'OAuthFlow | None' = None
    authorization_code: 'OAuthFlow | None' = None
