from http import HTTPStatus
from typing import Any, ClassVar, Generic, TypeAlias, TypeVar, get_args

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse
from django.views import View
from typing_extensions import override

from django_modern_rest.components import ComponentParser
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import (
    MethodNotAllowedError,
    SerializationError,
    UnsolvableAnnotationsError,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import (
    Empty,
    EmptyObj,
    infer_bases,
    infer_type_args,
)

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)

_ComponentParserSpec: TypeAlias = tuple[
    type[ComponentParser],
    tuple[Any, ...],
]


class Controller(View, Generic[_SerializerT]):  # noqa: WPS214
    """Defines API views as controllers."""

    # Public API:
    endpoint_cls: ClassVar[type[Endpoint]] = Endpoint
    api_endpoints: ClassVar[dict[str, Endpoint]]

    # We lie about that it is an instance variable, because type vars
    # are not allowed in `ClassVar`:
    _serializer: type[BaseSerializer]

    # Internal API:
    _component_parsers: ClassVar[list[_ComponentParserSpec]]
    _current_endpoint: Endpoint

    @override
    def __init_subclass__(cls) -> None:
        """Collect components parsers."""
        super().__init_subclass__()
        type_args = infer_type_args(cls, Controller)
        if len(type_args) != 1:
            raise UnsolvableAnnotationsError(
                f'Type args {type_args} are not correct for {cls}, '
                'only 1 type arg must be provided',
            )
        if isinstance(type_args[0], TypeVar):
            return  # This is a generic subclass of a controller.
        if not issubclass(type_args[0], BaseSerializer):
            raise UnsolvableAnnotationsError(
                f'Type arg {type_args[0]} are not correct for {cls}, '
                'it must be a BaseSerializer subclass',
            )
        cls._serializer = type_args[0]
        cls._component_parsers = [
            (subclass, get_args(subclass))
            for subclass in infer_bases(cls, ComponentParser)
        ]
        cls.api_endpoints = {
            meth: cls.endpoint_cls(func, serializer=cls._serializer)
            for meth in cls.existing_http_methods()
            if (func := getattr(cls, meth)) is not getattr(View, meth, None)
        }
        cls._validate_endpoints()

    def to_response(
        self,
        raw_data: Any,
        *,
        headers: dict[str, str] | Empty = EmptyObj,
        status_code: HTTPStatus | Empty = EmptyObj,
    ) -> HttpResponse:
        """
        Helpful method to convert response parts into an actual response.

        Should be always used instead of using
        raw :class:`django.http.HttpResponse` objects.
        Has better serialization speed and semantics than manual.
        Does the usual validation, no "second validation" problem exists.
        """
        # For mypy: this can't be `None` at this point.
        return self._current_endpoint.to_response(
            self._serializer,
            raw_data=raw_data,
            headers=headers,
            status_code=status_code,
        )

    @override
    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Parse all components before the dispatching and call controller."""
        try:
            return self._handle_request(request, *args, **kwargs)
        except SerializationError as exc:
            if self._current_endpoint.is_async:
                # We have to lie here, because of how `View.dispatch` is typed.
                # Nothing we can do :(
                return self._async_handle_error(exc)  # type: ignore[return-value]
            return self._handle_error(exc)
        except MethodNotAllowedError:
            # This is the only case when we don't set `self._current_endpoint`
            # TODO: write our own `http_method_not_allowed` handler
            return self.http_method_not_allowed(request, *args, **kwargs)

    @classmethod
    def existing_http_methods(cls) -> set[str]:
        """Returns and caches what HTTP methods are implemented in this view."""
        return {
            method
            for method in cls.http_method_names
            if getattr(cls, method, None) is not None
        }

    # Private API:

    @classmethod
    def _validate_endpoints(cls) -> None:
        """Validate that endpoints definition is correct in build time."""
        if not cls.api_endpoints:
            return
        is_async = cls.api_endpoints[
            next(iter(cls.api_endpoints.keys()))
        ].is_async
        if any(
            endpoint.is_async is not is_async
            for endpoint in cls.api_endpoints.values()
        ):
            # The same error message that django has.
            raise ImproperlyConfigured(
                f'{cls!r} HTTP handlers must either be all sync or all async.',
            )

    def _handle_request(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        # Fast path for method resolution:
        endpoint = self.api_endpoints.get(request.method.lower())  # type: ignore[union-attr]
        if endpoint is not None:
            self._current_endpoint = endpoint
            # TODO: support `StreamingHttpResponse`
            for parser, type_args in self._component_parsers:
                # TODO: maybe parse all at once?
                # See https://github.com/wemake-services/django-modern-rest/issues/8
                parser.parse_component(  # pyright: ignore[reportPrivateUsage]
                    # We lie that this is a `ComponentParser`, but their
                    # APIs are compatible by design.
                    self,  # type: ignore[arg-type]
                    self._serializer,
                    type_args,
                    request,
                    *args,
                    **kwargs,
                )
            return endpoint(self, *args, **kwargs)  # we don't pass request
        raise MethodNotAllowedError

    # TODO: think about `error` and `handle_error` API. This should be public.
    def _handle_error(self, exc: SerializationError) -> HttpResponse:
        """Return error response."""
        payload = {'detail': exc.args[0]}
        return self.to_response(payload, status_code=exc.status_code)

    async def _async_handle_error(
        self,
        exc: SerializationError,
    ) -> HttpResponse:
        """Async wrapper for the error handler."""
        return self._handle_error(exc)
