from dataclasses import dataclass
from typing import Final, cast

from dmr.openapi.objects import (  # noqa: WPS235
    Components,
    Contact,
    ExternalDocumentation,
    License,
    PathItem,
    Reference,
    SecurityRequirement,
    Server,
    Tag,
)

#: Oldest OpenAPI version we support: earlier ones are not JSON Schema based.
_MIN_OPENAPI_VERSION: Final = (3, 1)


@dataclass(slots=True, frozen=True, kw_only=True)
class OpenAPIConfig:
    """
    Configuration class for customizing OpenAPI specification metadata.

    This class provides a way to configure various aspects of the OpenAPI
    specification that will be generated for your API documentation. It allows
    you to customize the API information, contact details, licensing, security
    requirements, and other metadata that appears in the generated OpenAPI spec.

    Attributes:
        title: Human-readable title of the API,
            shown in the generated documentation.
        version: Version of your API
            (your application's own version, not the OpenAPI spec version).
        openapi_version: Version of the OpenAPI specification to target.
            Only ``'3.1.0'`` and newer versions are supported,
            because older ones are not based on JSON Schema.
            Defaults to ``'3.1.0'``.
        summary: Short, one-line summary of the API.
        description: Longer description of the API. May use CommonMark syntax.
        terms_of_service: URL to the terms of service for the API.
        contact: Contact information for the exposed API.
        external_docs: Link to additional external documentation.
        security: Global security requirements applied across the API.
            Each entry may be overridden per operation.
        license: License information for the exposed API.
        components: Reusable components (schemas, responses, parameters, etc.)
            to include in the spec.
        servers: Connectivity information for the target servers.
        tags: Metadata tags used to group operations in the documentation.
        webhooks: Webhook definitions that may be initiated by the API,
            keyed by name.

    .. versionchanged:: 0.16.0
        ``openapi_version`` older than ``'3.1.0'`` now raises a ``ValueError``.

    """

    title: str
    version: str
    openapi_version: str = '3.1.0'

    summary: str | None = None
    description: str | None = None
    terms_of_service: str | None = None
    contact: Contact | None = None
    external_docs: ExternalDocumentation | None = None
    security: list[SecurityRequirement] | None = None
    license: License | None = None
    # Components can't be a list in the final schema, so we merge them together:
    components: Components | list[Components] | None = None
    servers: list[Server] | None = None
    tags: list[Tag] | None = None
    webhooks: dict[str, PathItem | Reference] | None = None

    def __post_init__(self) -> None:
        """
        Validates that ``openapi_version`` is supported.

        Raises:
            ValueError: if ``openapi_version`` is older than ``'3.1.0'``.

        """
        # NOTE: we don't limit the upper bound on purpose,
        # we would only limit in the future if case
        # of a real incompatibility. There's a high chance
        # that it will just work (c)
        if self.openapi_version_info[:2] < _MIN_OPENAPI_VERSION:
            raise ValueError(
                'OpenAPI versions before 3.1.0 are not supported, because '
                'they are not based on JSON Schema, which is what we use '
                f'to generate model schemas, got {self.openapi_version!r}',
            )

    @property
    def openapi_version_info(self) -> tuple[int, int, int]:
        """
        Returns the parsed OpenAPI version.

        .. versionadded:: 0.8.0
        """
        return cast(
            'tuple[int, int, int]',
            tuple(map(int, self.openapi_version.split('.'))),
        )


def default_config() -> OpenAPIConfig:
    """Resolves the default config from settings."""
    from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

    config = resolve_setting(Settings.openapi_config)
    if not isinstance(config, OpenAPIConfig):
        raise TypeError(
            'OpenAPI config is not set. Please, set the '
            f'{str(Settings.openapi_config)!r} setting.',
        )
    return config
