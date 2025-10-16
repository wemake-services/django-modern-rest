from dataclasses import dataclass
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.oauth_flow import OAuthFlow


@dataclass(frozen=True, kw_only=True, slots=True)
class OAuthFlows(BaseObject):
    """TODO: add docs."""

    implicit: 'OAuthFlow | None' = None
    password: 'OAuthFlow | None' = None
    client_credentials: 'OAuthFlow | None' = None
    authorization_code: 'OAuthFlow | None' = None
