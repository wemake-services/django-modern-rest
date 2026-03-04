from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.openapi.objects.oauth_flow import OAuthFlow


@dataclass(kw_only=True)
class OAuthFlows:
    """Allows configuration of the supported OAuth Flows."""

    implicit: 'OAuthFlow | None' = None
    password: 'OAuthFlow | None' = None
    client_credentials: 'OAuthFlow | None' = None
    authorization_code: 'OAuthFlow | None' = None
