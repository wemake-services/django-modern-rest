import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Generic, TypeVar

from django.http import HttpRequest, HttpResponseBase
from django.utils.functional import classproperty
from django.views import View
from typing_extensions import override

from django_modern_rest.serialization import (
    BaseSerializer,
    ComponentParserMixin,
)
from django_modern_rest.types import infer_type_args

_ParserT = TypeVar('_ParserT', bound=BaseSerializer)


class RestEndpoint:
    """Wrapper for REST endpoint functions with serialization support."""

    __slots__ = ('_func',)

    _func: Callable[..., Any]

    def __init__(
        self,
        func: Callable[..., Any],
        *,  # TODO: add openapi metadata?
        parser: Callable[[Any], Any],
    ) -> None:
        """Initialize REST endpoint with function and serialization support."""
        if inspect.iscoroutinefunction(func):
            self._func = _async_serializer(func, parser)
        else:
            self._func = _sync_serializer(func, parser)

    def __call__(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Execute the wrapped function and return HTTP response."""
        return self._func(*args, **kwargs)  # type: ignore[no-any-return]


class Controller(View, Generic[_ParserT]):
    """Defines API views as controllers."""

    # Internal API:
    _component_parsers: ClassVar[list[ComponentParserMixin[Any]]]
    _api_endpoints: ClassVar[dict[str, RestEndpoint]]
    _parser: type[_ParserT]

    @override
    def __init_subclass__(cls) -> None:
        """Collect components parsers."""
        super().__init_subclass__()
        type_args = infer_type_args(cls, Controller)
        if len(type_args) != 1:
            raise ValueError(
                f'Type args {type_args} are not correct for {cls}, '
                'only 1 type arg must be provided',
            )
        cls._parser = type_args[0]

        if getattr(cls, '_component_parsers', None) is None:
            cls._component_parsers = [
                subclass()
                for subclass in cls.__mro__[1:]
                if issubclass(subclass, ComponentParserMixin)
            ]

        if getattr(cls, '_api_endpoints', None) is None:
            cls._api_endpoints = {
                method: RestEndpoint(getattr(cls, method), parser=cls._parser)
                for method in cls.existing_http_methods
            }

    @override
    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        """Parse all components before the dispatching and call controller."""
        for parser in self._component_parsers:
            # TODO: maybe parse all at once?
            parser._parse_component(request, *args, **kwargs)  # noqa: SLF001
        # Fast path for method resolution:
        endpoint = self._api_endpoints.get(request.method.lower())  # type: ignore[union-attr]
        if endpoint is not None:
            # TODO: validate `HttpResponse.content` with `return_dto`
            # TODO: support `StreamingHttpResponse`
            # TODO: support `JsonResponse`
            # TODO: use `return_dto` for schema generation
            # TODO: use configurable `json` encoders and decoders
            # TODO: make sure `return_dto` validation
            # can be turned off for production
            return endpoint(*args, **kwargs)  # we don't pass request
        return self.http_method_not_allowed(request, *args, **kwargs)

    @classproperty  # TODO: cache
    def existing_http_methods(cls) -> set[str]:  # noqa: N805
        """Returns and caches what HTTP methods are implemented in this view."""
        # TODO: validate that all handlers have `@rest` decorator
        return {
            method
            for method in cls.http_method_names
            if getattr(cls, method, None) is not None
        }


def _async_serializer(
    func: Callable[..., Any],
    parser: type[BaseSerializer],
) -> Callable[..., Awaitable[HttpResponseBase]]:
    @functools.wraps(func)
    async def decorator(*args: Any, **kwargs: Any) -> HttpResponseBase:
        result = await func(*args, **kwargs)
        return parser.to_response(result)

    return decorator


def _sync_serializer(
    func: Callable[..., Any],
    parser: type[BaseSerializer],
) -> Callable[..., HttpResponseBase]:
    @functools.wraps(func)
    def decorator(*args: Any, **kwargs: Any) -> HttpResponseBase:
        result = func(*args, **kwargs)
        return parser.to_response(result)

    return decorator
