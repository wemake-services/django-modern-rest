from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dmr.openapi.objects.oauth_flow import OAuthFlow


@dataclass(kw_only=True, slots=True)
class OAuthFlows:
    """
    Allows configuration of the supported OAuth Flows.

    .. versionchanged:: 0.16.0
        Added ``device_authorization`` from OpenAPI 3.2.
        Added ``x_extensions`` for specification extensions.

    """

    implicit: 'OAuthFlow | None' = None
    password: 'OAuthFlow | None' = None
    client_credentials: 'OAuthFlow | None' = None
    authorization_code: 'OAuthFlow | None' = None

    # OpenAPI 3.2+ fields:
    device_authorization: 'OAuthFlow | None' = None
    #: Specification extensions, keys must start with ``x-``.
    x_extensions: dict[str, Any] | None = None
