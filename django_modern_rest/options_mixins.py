from http import HTTPStatus
from typing import TYPE_CHECKING, Final

from django.http import HttpResponse

from django_modern_rest.endpoint import validate
from django_modern_rest.headers import HeaderSpec
from django_modern_rest.metadata import ResponseSpec

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.serializer import BaseSerializer


#: Metadata for the default options response.
OptionsResponse: Final = ResponseSpec(
    None,
    status_code=HTTPStatus.NO_CONTENT,
    headers={'Allow': HeaderSpec()},
)


class MetaMixin:
    """
    Mixing that provides default ``meta`` method or ``OPTIONS`` http method.

    Use it for sync controllers.

    It just returns the list of allowed methods.
    Use it as a mixin with
    the :class:`django_modern_rest.controller.Controller` type:

    .. code:: python

        >>> from django_modern_rest import Controller
        >>> from django_modern_rest.options_mixins import MetaMixin
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class SupportsOptionsHttpMethod(
        ...     MetaMixin,
        ...     Controller[PydanticSerializer],
        ... ): ...

    """

    __slots__ = ()

    @validate(OptionsResponse)
    def meta(self) -> HttpResponse:
        """Default sync implementation for ``OPTIONS`` http method."""
        return _meta_impl(self)  # type: ignore[arg-type]


class AsyncMetaMixin:
    """
    Mixing that provides default ``meta`` method or ``OPTIONS`` http method.

    Use it for async controllers.

    It just returns the list of allowed methods.
    Use it as a mixin with
    the :class:`django_modern_rest.controller.Controller` type:

    .. code:: python

        >>> from django_modern_rest import Controller
        >>> from django_modern_rest.options_mixins import AsyncMetaMixin
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class SupportsOptionsHttpMethod(
        ...     AsyncMetaMixin,
        ...     Controller[PydanticSerializer],
        ... ): ...

    """

    __slots__ = ()

    @validate(OptionsResponse)
    async def meta(self) -> HttpResponse:
        """Default async implementation for ``OPTIONS`` http method."""
        return _meta_impl(self)  # type: ignore[arg-type]


def _meta_impl(controller: 'Controller[BaseSerializer]') -> HttpResponse:
    allow = ', '.join(
        method for method in sorted(controller.api_endpoints.keys())
    )
    return controller.to_response(
        raw_data=None,
        status_code=HTTPStatus.NO_CONTENT,
        headers={'Allow': allow},
    )
