from http import HTTPStatus
from typing import Any, ClassVar, Generic, TypeAlias, TypeVar, get_args

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse
from django.views import View
from typing_extensions import deprecated, override

from django_modern_rest.components import ComponentParser
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import (
    MethodNotAllowedError,
    SerializationError,
    UnsolvableAnnotationsError,
)
from django_modern_rest.response import build_response
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
        assert self.request.method  # noqa: S101
        return build_response(
            self.request.method,
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
            if self.view_is_async:
                # We have to lie here, because of how `View.dispatch` is typed.
                # Nothing we can do :(
                return self._async_handle_error(exc)  # type: ignore[return-value]
            return self._handle_error(exc)
        except MethodNotAllowedError as exc:
            return self.handle_method_not_allowed(exc.method)

    @override
    @deprecated(
        # It is not actually deprecated, but type checkers have no other
        # ways to raise custom errors.
        'Please do not use this method with `django-modern-rest`, '
        'use `handle_method_not_allowed` instead',
    )
    def http_method_not_allowed(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Do not use, use :meth:`handle_method_not_allowed` instead.

        ``View.http_method_not_allowed`` raises an error in a wrong format.
        """
        raise NotImplementedError(
            'Please do not use this method with `django-modern-rest`, '
            'use `handle_method_not_allowed` instead',
        )

    @classmethod
    def handle_method_not_allowed(
        cls,
        method: str,
    ) -> HttpResponse:
        """
        Return error response for 405 response code.

        It is special in way that we don't have an endpoint associated with it.
        """
        # This method cannot call `self.to_response`, because it does not have
        # an endpoint associated with it. We switch to lower level
        # `build_response` primitive
        allowed_methods = sorted(cls.existing_http_methods())
        response = build_response(
            None,
            cls._serializer,
            raw_data={
                'detail': (
                    f'Method {method!r} is not allowed, '
                    f'allowed: {allowed_methods!r}'
                ),
            },
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )
        if cls.view_is_async:
            # We have to do that the same way original Django does.
            # It is not THAT slow, because it happens only when 405 happens.
            # Which is not really that frequent.
            async def factory() -> HttpResponse:  # noqa: RUF029, WPS430
                return response

            # And again we have to lie to django :(
            return factory()  # type: ignore[return-value]

        return response

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
                f'{cls!r} HTTP handlers must either be all sync or all async',
            )

    def _handle_request(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        # Fast path for method resolution:
        method = request.method.lower()  # type: ignore[union-attr]
        endpoint = self.api_endpoints.get(method)
        if endpoint is not None:
            # TODO: support `StreamingHttpResponse`
            # TODO: support `FileResponse`
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
        raise MethodNotAllowedError(method)

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
