from collections.abc import Callable, Mapping, Sequence, Set
from http import HTTPMethod, HTTPStatus
from typing import Any, ClassVar, Final, Generic, TypeAlias, TypeVar

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.urls import URLPattern
from django.utils.functional import classproperty
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from typing_extensions import deprecated, override

from dmr.cookies import NewCookie
from dmr.endpoint import Endpoint
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.internal.io import identity
from dmr.metadata import ResponseSpec
from dmr.negotiation import request_renderer
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.objects import PathItem, Server
from dmr.parsers import Parser
from dmr.renderers import Renderer
from dmr.response import build_response
from dmr.security.base import AsyncAuth, SyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import HttpSpec
from dmr.types import infer_type_args
from dmr.validation import ControllerValidator, SettingsValidator

_METHOD_NOT_ALLOWED_MSG: Final = _(
    'Method {method} is not allowed, allowed: {allowed}',
)

_SerializerT_co = TypeVar(
    '_SerializerT_co',
    bound=BaseSerializer,
    covariant=True,
)

_ResponseT = TypeVar('_ResponseT', bound=HttpResponse)

_EndpointFunc: TypeAlias = Callable[..., Any]


class Controller(Generic[_SerializerT_co], View):  # noqa: WPS214
    """
    Defines API views as controllers.

    Controller is a :class:`django.views.generic.base.View` subclass
    that should be used as a base for all REST endpoints.

    Attributes:
        endpoint_cls: Class to create endpoints with.
        serializer: Serializer that is passed via type parameters.
            The main goal of the serializer is to serialize object
            to json and deserialize them from json.
            You can't change the serializer simply by modifying
            the attribute in the controller class.
            Because it is already passed to many other places.
            To customize it: create a new class,
            subclass :class:`~dmr.serializer.BaseSerializer`,
            and pass the new type as a type argument to the controller.
        settings_validator_cls: Runs settings validation
            once the first controller is created.
        no_validate_http_spec: Set of http spec validation checks
            that we disable for this class.
        validate_responses: Boolean whether or not validating responses.
            Works in runtime, can be disabled for better performance.
        semantic_responses: Should semantic responses be collected
            from different providers for all endpoints in this class.
        exclude_semantic_responses: Set of semantic responses
            that user wants to disable.
        validate_events: Should this endpoint validate events?
            If not set, defaults to the ``validate_responses`` value.
            This value only matters if the response
            will be a streaming response that supports event validation.
        responses: List of responses schemas that this controller can return.
            Also customizable in endpoints and globally with ``'responses'``
            key in the settings.
        allowed_http_methods: Set of names to be treated as names for endpoints.
            Does not include ``options``, but includes ``meta``.
        parsers: Sequence of parsers to be used for this controller
            to parse incoming request's body. All instances must be of subtypes
            of :class:`~dmr.parsers.Parser`.
        renderers: Sequence of renderers to be used for this controller
            to render response's body. All instances must be of subtypes
            of :class:`~dmr.renderers.Renderer`.
        auth: Sequence of auth instances to be used for this controller.
            Sync controllers must use instances
            of :class:`dmr.security.SyncAuth`.
            Async controllers must use instances
            of :class:`dmr.security.AsyncAuth`.
            Set it to ``None`` to disable auth of this controller.
        error_model: Schema type that represents
            and validates common error responses.
        is_abstract: Whether or not this controller is abstract.
            We consider controller "abstract" when it does not have
            exact serializer type.
        streaming: Does this controller work with streaming responses like SSE?
        controller_validator_cls: Runs full controller validation on definition.
        api_endpoints: Dictionary of HTTPMethod name to controller instance.
        csrf_exempt: Should this controller be exempted from the CSRF check?
            Is ``True`` by default.
        summary: A short summary of what this path item does.
        description: A verbose explanation of the path item behavior.
        servers: An alternative servers array to service this path item.
        request: Current :class:`~django.http.HttpRequest` instance.
        args: Path positional parameters of the request.
        kwargs: Path named parameters of the request.

    """

    # Public class-level API:
    controller_validator_cls: ClassVar[type[ControllerValidator]] = (
        ControllerValidator
    )
    settings_validator_cls: ClassVar[type[SettingsValidator]] = (
        SettingsValidator
    )
    api_endpoints: ClassVar[Mapping[str, Endpoint]]
    csrf_exempt: ClassVar[bool] = True
    serializer: ClassVar[type[BaseSerializer]]
    endpoint_cls: ClassVar[type[Endpoint]] = Endpoint
    no_validate_http_spec: ClassVar[Set[HttpSpec] | None] = frozenset()
    validate_responses: ClassVar[bool | None] = None
    semantic_responses: ClassVar[bool | None] = None
    exclude_semantic_responses: ClassVar[Set[HTTPStatus] | None] = frozenset()
    validate_events: ClassVar[bool | None] = None
    responses: ClassVar[Sequence[ResponseSpec]] = []
    allowed_http_methods: ClassVar[Set[str]] = frozenset(
        # We replace old existing `View.options` method with modern `meta`:
        {method.name.lower() for method in HTTPMethod} - {'options'} | {'meta'},
    )
    parsers: ClassVar[Sequence[Parser]] = ()
    renderers: ClassVar[Sequence[Renderer]] = ()
    auth: ClassVar[Sequence[SyncAuth] | Sequence[AsyncAuth] | None] = ()
    error_model: ClassVar[Any] = ErrorModel
    is_abstract: ClassVar[bool] = True
    streaming: ClassVar[bool] = False

    # OpenAPI:
    summary: ClassVar[str | None] = None
    description: ClassVar[str | None] = None
    servers: ClassVar[Sequence[Server] | None] = None

    # Public instance API:
    request: HttpRequest
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    # Protected API:
    _is_async: ClassVar[bool | None] = None  # `None` means that nothing's found

    @override
    def __init_subclass__(cls) -> None:
        """Construct a controller."""
        super().__init_subclass__()
        serializer = cls._infer_serializer()
        if serializer is None:
            return  # this is an abstract controller

        cls.is_abstract = False
        cls.serializer = serializer
        cls.settings_validator_cls(serializer=cls.serializer)()

        # Now it is validated that we don't have intersections.
        cls.api_endpoints = {
            canonical: cls.endpoint_cls(
                meth,
                controller_cls=cls,
            )
            for canonical, meth in cls._find_existing_http_methods().items()
        }
        cls._is_async = cls.controller_validator_cls()(cls)

    @override
    @classmethod
    def as_view(cls, **initkwargs: Any) -> Callable[..., HttpResponseBase]:
        """
        Returns a view function for the class-based view.

        This override applies CSRF exemption to the view. Session-based
        authentication will still be explicitly validated for CSRF,
        while all other authentication methods will be CSRF-exempt.
        """
        return (
            csrf_exempt(super().as_view(**initkwargs))
            if cls.csrf_exempt
            else super().as_view(**initkwargs)
        )

    @override
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        """
        Set request context.

        Unlike :meth:`~django.views.generic.base.View.setup` does not set
        ``head`` method automatically.

        Thread safety: there's only one controller instance per request.
        """
        self.request = request
        self.args = args
        self.kwargs = kwargs

    @override
    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        """
        Find an endpoint that serves this HTTP method and call it.

        Return 405 if this method is not allowed.
        """
        # Fast path for method resolution:
        method: str = request.method  # type: ignore[assignment]
        endpoint = self.api_endpoints.get(method)
        if endpoint is not None:
            return endpoint(self, *args, **kwargs)
        # This return is very special,
        # since it does not have an attached endpoint.
        # All other responses are handled on endpoint level
        # with all the response type validation.
        return self.handle_method_not_allowed(method)

    def to_response(
        self,
        raw_data: Any,
        *,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        status_code: HTTPStatus | None = None,
        renderer: Renderer | None = None,
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
            self.serializer,
            method=self.request.method,
            raw_data=raw_data,
            headers=headers,
            cookies=cookies,
            status_code=status_code,
            renderer=renderer or request_renderer(self.request),
        )

    def to_error(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        renderer: Renderer | None = None,
    ) -> HttpResponse:
        """
        Helpful method to convert API error parts into an actual error.

        Always requires the error code to be passed.

        Should be always used instead of using
        raw :class:`django.http.HttpResponse` objects.
        Does the usual validation, no "second validation" problem exists.
        """
        return build_response(
            self.serializer,
            raw_data=raw_data,
            headers=headers,
            cookies=cookies,
            status_code=status_code,
            renderer=(
                renderer
                or request_renderer(
                    self.request,
                    use_nonstreaming_renderer=True,
                )
            ),
        )

    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> Any:  # `Any`, so we can change the return type in subclasses.
        """
        Convert error to the common format.

        Args:
            error: A serialization exception like a validation error.
            loc: Location where this error happened.
                Like ``"headers"``, or ``"field_name"``,
                or ``["parsed_headers", "header_name"]``.
            error_type: Optional type of the error for extra metadata.

        Returns:
            Simple python object - exception converted to a common format.

        """
        return format_error(error, loc=loc, error_type=error_type)

    def handle_error(
        self,
        endpoint: Endpoint,
        controller: 'Controller[_SerializerT_co]',
        exc: Exception,
    ) -> HttpResponse:
        """
        Return error response if possible. Sync case.

        Override this method to add custom error handling for sync execution.
        By default - does nothing, only re-raises the passed error.
        Won't be called when using async endpoints.
        """
        raise exc from None

    async def handle_async_error(
        self,
        endpoint: Endpoint,
        controller: 'Controller[_SerializerT_co]',
        exc: Exception,
    ) -> HttpResponse:
        """
        Return error response if possible. Async case.

        Override this method to add custom error handling for async execution.
        By default - does nothing, only re-raises the passed error.
        Won't be called when using sync endpoints.
        """
        raise exc from None

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

    @override
    @deprecated(
        # It is not actually deprecated, but type checkers have no other
        # ways to raise custom errors.
        'Please do not use `options` method with `django-modern-rest`, '
        'define your own `meta` method instead',
    )
    def options(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Do not use, define your own `meta` method instead.

        Django's `View.options` has incompatible signature with
        ``django-modern-rest``. It would be a typing error
        to define something like:

        .. warning::

            Don't do this!

            .. code:: python

                >>> from http import HTTPStatus
                >>> from dmr import Controller, validate
                >>> from dmr.plugins.pydantic import (
                ...     PydanticSerializer,
                ... )
                >>> class MyController(Controller[PydanticSerializer]):
                ...     @validate(
                ...         ResponseSpec(
                ...             None,
                ...             status_code=HTTPStatus.NO_CONTENT,
                ...         ),
                ...     )
                ...     def options(self) -> HttpResponse:  # <- typing problem
                ...         ...

        That's why instead of ``options`` you should define
        our own ``meta`` method:

        .. code:: python

           >>> class MyController(Controller[PydanticSerializer]):
           ...     @validate(
           ...         ResponseSpec(
           ...             None,
           ...             status_code=HTTPStatus.NO_CONTENT,
           ...         ),
           ...     )
           ...     def meta(self) -> HttpResponse:
           ...         allow = ','.join(
           ...             method.upper()
           ...             for method in self.allowed_http_methods
           ...         )
           ...         return self.to_response(
           ...             None,
           ...             status_code=HTTPStatus.NO_CONTENT,
           ...             headers={'Allow': allow},
           ...         )

        .. note::

            By default ``meta`` method is not provided for you.
            If you want to support ``OPTIONS`` http method
            with the default implementation, use:

            .. code:: python

               >>> from dmr.options_mixins import MetaMixin

               >>> class ControllerWithMeta(
               ...     MetaMixin,
               ...     Controller[PydanticSerializer],
               ... ): ...

        """
        raise NotImplementedError(
            'Please do not use `options` method with `django-modern-rest`, '
            'define your own `meta` method instead',
        )

    def handle_method_not_allowed(
        self,
        method: str,
    ) -> HttpResponse:
        """
        Return error response for 405 response code.

        It is special in way that we don't have an endpoint associated with it.
        """
        # This method cannot call `self.to_response`, because it does not have
        # an endpoint associated with it. We switch to lower level
        # `build_response` primitive
        allowed_methods = sorted(self.api_endpoints.keys())
        # NOTE: this response is not validated, so be careful with the spec!
        return self._maybe_wrap(
            build_response(
                self.serializer,
                raw_data=self.format_error(
                    _METHOD_NOT_ALLOWED_MSG.format(
                        method=repr(method),
                        allowed=repr(allowed_methods),
                    ),
                    error_type=ErrorType.not_allowed,
                ),
                status_code=HTTPStatus.METHOD_NOT_ALLOWED,
                headers={'Allow': ', '.join(allowed_methods)},
                renderer=request_renderer(self.request),
            ),
        )

    @classmethod
    def get_path_item(
        cls,
        path: str,
        pattern: URLPattern,
        context: OpenAPIContext,
    ) -> PathItem:
        """Generate OpenAPI spec for path items."""
        operations: dict[str, Any] = {
            method.lower(): endpoint.get_schema(
                path,
                pattern,
                cls.__qualname__,
                cls.serializer,
                context,
            )
            for method, endpoint in cls.api_endpoints.items()
        }
        return PathItem(
            **operations,
            summary=cls.summary,
            description=cls.description,
            servers=None if cls.servers is None else list(cls.servers),
        )

    @classproperty
    @override
    def view_is_async(cls) -> bool:  # noqa: N805  # pyright: ignore[reportIncompatibleVariableOverride]  # pyrefly: ignore[bad-override]
        """We already know this in advance, no need to recalculate."""
        return cls._is_async is True

    # Protected API:

    @classmethod
    def _infer_serializer(cls) -> type[_SerializerT_co] | None:
        type_args = infer_type_args(cls, Controller)
        if not type_args:
            raise UnsolvableAnnotationsError(
                f'Type args {type_args} are not correct for {cls}, '
                'at least 1 type arg must be provided',
            )
        serializer = type_args[0]
        if isinstance(serializer, TypeVar):
            return None  # This is a generic subclass of a controller.
        if (
            not issubclass(serializer, BaseSerializer)
            or serializer is BaseSerializer
        ):
            raise UnsolvableAnnotationsError(
                f'Type arg {serializer} is not correct for {cls}, '
                'it must be a BaseSerializer subclass',
            )
        return serializer  # type: ignore[no-any-return]

    @classmethod
    def _maybe_wrap(
        cls,
        response: _ResponseT,
    ) -> _ResponseT:
        """Wraps response into a coroutine if this is an async controller."""
        if cls._is_async:
            return identity(response)
        return response

    @classmethod
    def _find_existing_http_methods(cls) -> dict[str, Callable[..., Any]]:
        """
        Returns what HTTP methods are implemented in this controller.

        Returns both canonical http method name and our dsl name.
        """
        return {
            # Rename `meta` back to `options`:
            ('OPTIONS' if dsl_method == 'meta' else dsl_method.upper()): method
            for dsl_method in cls.allowed_http_methods
            if (method := getattr(cls, dsl_method, None)) is not None
        }
