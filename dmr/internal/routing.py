import dataclasses
from typing import TYPE_CHECKING, Self, final

from django.urls.resolvers import URLPattern

from dmr.openapi.objects import PathItem

if TYPE_CHECKING:
    from dmr.routing import Router


@final
@dataclasses.dataclass(slots=True, frozen=True)
class URLExternal:
    """
    Represents an external URL that was added to the routing of DMR.

    Prefer :func:`external_path` over using this class directly.
    See :ref:`external-views` for more info.

    .. versionadded:: 0.13.0
    .. versionchanged:: 0.14.0
        Moved to internal and made protected.

    """

    url: URLPattern
    openapi: PathItem | None = dataclasses.field(kw_only=True)

    def get_url_with_metadata(self) -> URLPattern:
        """Get the url pattern with attached OpenAPI metadata."""
        self.url.callback.__dmr_external_openapi__ = self.openapi  # type: ignore[attr-defined]
        return self.url


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class RouterMetadata:
    """
    Used to represent the metadata that we apply from router to all operations.

    Must contain all the metadata fields from :class:`dmr.routing.Router`.

    .. versionadded:: 0.15.0
    """

    tags: list[str]
    deprecated: bool
    ignore_from_spec: bool

    @classmethod
    def from_router(cls, router: 'Router') -> Self:
        """Create metadata from router instance."""
        return cls(
            tags=router.tags,
            deprecated=router.deprecated,
            ignore_from_spec=router.ignore_from_spec,
        )

    @classmethod
    def from_included(cls, router: 'Router', included: Self) -> Self:
        """Create metadata from included and including routers."""
        return cls(
            tags=router.tags + included.tags,
            deprecated=router.deprecated or included.deprecated,
            ignore_from_spec=(
                router.ignore_from_spec or included.ignore_from_spec
            ),
        )
