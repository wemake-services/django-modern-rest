from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.oauth_flows import OAuthFlows


@dataclass(frozen=True, kw_only=True, slots=True)
class SecurityScheme(BaseObject):
    """TODO: add docs."""

    type: Literal['apiKey', 'http', 'mutualTLS', 'oauth2', 'openIdConnect']
    description: str | None = None
    name: str | None = None
    security_scheme_in: Literal['query', 'header', 'cookie'] | None = None
    scheme: str | None = None
    bearer_format: str | None = None
    flows: 'OAuthFlows | None' = None
    open_id_connect_url: str | None = None
