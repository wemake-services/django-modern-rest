from collections.abc import Callable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, TypeVar, final

from typing_extensions import override

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

_HttpPartT = TypeVar('_HttpPartT')


@final
class FromController(Mapping[str, _HttpPartT]):
    """
    Lazy mapping of response headers or cookies defined by a controller.

    Reusable controllers declare ``@validate`` and ``@modify`` once,
    on the base class. But header and cookie names are usually only known
    on the final subclass, because they are configured with ``ClassVar``s.
    This object defers the lookup: we remember the name of a ``classmethod``
    and call it on the concrete controller,
    when its endpoint metadata is built.

    .. code:: python

        >>> from collections.abc import Mapping
        >>> from typing import ClassVar

        >>> from dmr import CookieSpec, FromController

        >>> class _Example:
        ...     access_cookie: ClassVar[str] = 'access_token'
        ...
        ...     @classmethod
        ...     def cookie_specs(cls) -> Mapping[str, CookieSpec]:
        ...         return {cls.access_cookie: CookieSpec(httponly=True)}

        >>> class _Custom(_Example):
        ...     access_cookie: ClassVar[str] = 'custom_token'

        >>> lazy = FromController(_Example.__dict__['cookie_specs'])
        >>> list(lazy.resolve(_Custom))
        ['custom_token']

    We look the method up by name and not by the stored function object,
    so subclasses can override the method itself,
    not just the ``ClassVar`` values that it reads.

    This mapping is not usable until it is resolved:
    any attempt to read it raises :class:`~dmr.exceptions.EndpointMetadataError`
    instead of silently returning something wrong.

    .. versionadded:: 0.15.0

    """

    __slots__ = ('_method_name',)

    def __init__(
        self,
        method: Callable[[Any], Mapping[str, _HttpPartT]],
    ) -> None:
        """
        We only store the method's name, the lookup happens later.

        Inside a class body *method* is still a raw ``classmethod`` object,
        which is not callable on its own since Python 3.13.
        That is why we unwrap it instead of just keeping the callable.
        """
        self._method_name = getattr(method, '__func__', method).__name__

    @override
    def __repr__(self) -> str:
        """Unresolved mappings show up in error messages, be helpful there."""
        return f'{type(self).__name__}({self._method_name!r})'

    @override
    def __getitem__(self, key: str) -> _HttpPartT:
        """This mapping has no items before it is resolved."""
        raise self._unresolved_error()

    @override
    def __iter__(self) -> Iterator[str]:
        """This mapping has no keys before it is resolved."""
        raise self._unresolved_error()

    @override
    def __len__(self) -> int:
        """This mapping has no length before it is resolved."""
        raise self._unresolved_error()

    def resolve(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> Mapping[str, _HttpPartT]:
        """Call the wrapped ``classmethod`` on the concrete controller."""
        return dict(getattr(controller_cls, self._method_name)())

    def _unresolved_error(self) -> Exception:
        from dmr.exceptions import EndpointMetadataError  # noqa: PLC0415

        return EndpointMetadataError(
            f'{self!r} was used outside of `@validate` or `@modify`, '
            'it can only be read after it is resolved '
            'against a concrete controller',
        )


def resolve_lazy_http_parts(
    http_parts: Mapping[str, _HttpPartT] | None,
    controller_cls: type['Controller[BaseSerializer]'],
) -> Mapping[str, _HttpPartT] | None:
    """Turn a :class:`FromController` mapping into a regular one."""
    if isinstance(http_parts, FromController):
        return http_parts.resolve(controller_cls)
    return http_parts
