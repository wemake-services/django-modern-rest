import abc
from typing import Any, ClassVar, Generic, TypeVar

from django.http import HttpRequest, HttpResponse

_ModelT = TypeVar('_ModelT')


class RequestParserMixin(Generic[_ModelT]):
    """Base abtract parser for request components."""

    __is_base_type__: ClassVar[bool] = True

    # We lie that it is an isntance attribute, but
    # we can't use type vars in class attrs.
    __model__: type[_ModelT]

    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Mixin method to parse things from django's request."""
        self._parse_component(request, *args, **kwargs)
        # Since it is used as a mixing, `dispatch` will be there:
        return super().dispatch(  # type: ignore[no-any-return, misc]
            request,
            *args,
            **kwargs,
        )

    @abc.abstractmethod
    def _parse_component(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        raise NotImplementedError
