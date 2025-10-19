from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, final

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.oauth_flows import OAuthFlows


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class SecurityScheme(BaseObject):
    """
    Defines a security scheme that can be used by the operations.

    Supported schemes are HTTP authentication, an API key
    (either as a header, a cookie parameter or as a query parameter),
    mutual TLS (use of a client certificate),
    OAuth2's common flows (implicit, password, client credentials
    and authorization code) as defined in RFC6749, and OpenID Connect Discovery.
    Please note that as of 2020, the implicit flow is about to be deprecated by
    OAuth 2.0 Security Best Current Practice.
    Recommended for most use case is Authorization Code Grant flow with PKCE.
    """

    type: Literal['apiKey', 'http', 'mutualTLS', 'oauth2', 'openIdConnect']
    description: str | None = None
    name: str | None = None
    security_scheme_in: Literal['query', 'header', 'cookie'] | None = None
    scheme: str | None = None
    bearer_format: str | None = None
    flows: 'OAuthFlows | None' = None
    open_id_connect_url: str | None = None
