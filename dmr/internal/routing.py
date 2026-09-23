import dataclasses
from typing import TYPE_CHECKING, Any, Self, TypeAlias, final

from django.urls.resolvers import RoutePattern
from typing_extensions import override

if TYPE_CHECKING:
    from dmr.routing import Router


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


_CapturedArgs: TypeAlias = tuple[Any, ...]
_CapturedKwargs: TypeAlias = dict[str, int | str]
_RouteMatch: TypeAlias = tuple[str, _CapturedArgs, _CapturedKwargs]


@final
class PrefixRoutePattern(RoutePattern):
    """Custom route pattern for better speed."""

    def __init__(
        self,
        route: str,
        name: str | None = None,
        is_endpoint: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Static patterns would work faster."""
        idx = route.find('<')
        if idx == -1:
            self._prefix = route
            self._is_static = True
        else:
            self._is_static = False
            self._prefix = route[:idx]
        self._is_endpoint = is_endpoint
        super().__init__(route, name, is_endpoint)

    @override
    def match(
        self,
        path: str,
    ) -> _RouteMatch | None:
        if self._is_static:
            if self._is_endpoint and path == self._prefix:
                return '', (), {}
            if not self._is_endpoint and path.startswith(self._prefix):
                return path[len(self._prefix) :], (), {}
        elif path.startswith(self._prefix):
            return super().match(path)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        return None
