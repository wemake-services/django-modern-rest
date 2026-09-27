from dataclasses import dataclass


@dataclass(kw_only=True, slots=True)
class OAuthFlow:
    """
    Configuration details for a supported OAuth Flow.

    .. versionchanged:: 0.16.0
        Added ``device_authorization_url`` from OpenAPI 3.2.

    """

    authorization_url: str | None = None
    token_url: str | None = None
    refresh_url: str | None = None
    scopes: dict[str, str] | None = None

    # OpenAPI 3.2+ fields:
    #: Required by the ``device_authorization`` flow, see RFC8628.
    device_authorization_url: str | None = None
