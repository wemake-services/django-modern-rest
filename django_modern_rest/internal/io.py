from typing import TYPE_CHECKING, TypeVar

_ItemT = TypeVar('_ItemT')


if TYPE_CHECKING:

    def identity(wrapped: _ItemT) -> _ItemT:
        """We still need to lie in type annotations. I am sad."""
        raise NotImplementedError

else:

    async def identity(wrapped: _ItemT) -> _ItemT:  # noqa: RUF029
        """
        Just returns an object wrapped in a coroutine.

        Needed for django view handling, where async views
        require coroutine return types.
        """
        return wrapped
