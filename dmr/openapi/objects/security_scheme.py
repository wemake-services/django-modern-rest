from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Literal

from dmr.internal.dataclass_aliases import Field

if TYPE_CHECKING:
    from dmr.openapi.objects.oauth_flows import OAuthFlows


@dataclass(kw_only=True, slots=True)
class SecurityScheme:
    """
    Defines a security scheme that can be used by the operations.

    Supported schemes are HTTP authentication, an API key
    (either as a header, a cookie parameter or as a query parameter),
    mutual TLS (use of a client certificate),
    OAuth2's common flows (implicit, password, client credentials
    and authorization code) as defined in RFC6749,
    OAuth2's device authorization flow as defined in RFC8628,
    and OpenID Connect Discovery.
    Please note that as of 2020, the implicit flow is about to be deprecated by
    OAuth 2.0 Security Best Current Practice.
    Recommended for most use cases is Authorization Code Grant flow with PKCE.

    .. versionchanged:: 0.16.0
        Added ``oauth2_metadata_url`` and ``deprecated`` from OpenAPI 3.2.

    """

    type: Literal['apiKey', 'http', 'mutualTLS', 'oauth2', 'openIdConnect']
    description: str | None = None
    name: str | None = None
    security_scheme_in: Annotated[
        Literal['query', 'header', 'cookie'] | None,
        Field(alias='in'),
    ] = None
    scheme: str | None = None
    bearer_format: str | None = None
    flows: 'OAuthFlows | None' = None
    open_id_connect_url: str | None = None

    # OpenAPI 3.2+ fields:
    #: URL of the OAuth2 authorization server metadata, see RFC8414.
    #: Only applies to the ``oauth2`` type.
    oauth2_metadata_url: str | None = None
    deprecated: bool | None = None
