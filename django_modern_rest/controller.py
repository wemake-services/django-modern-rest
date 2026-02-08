from collections.abc import Callable, Mapping, Sequence, Set
from http import HTTPMethod, HTTPStatus
from typing import (
    Any,
    ClassVar,
    Generic,
    TypeAlias,
    TypeVar,
)

from django.http import HttpRequest, HttpResponse
from django.utils.functional import cached_property, classproperty
from django.views import View
from typing_extensions import deprecated, override

from django_modern_rest.components import (
    ComponentParserBuilder,
    ComponentParserSpec,
)
from django_modern_rest.cookies import CookieSpec, NewCookie
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.errors import ErrorModel, ErrorType, format_error
from django_modern_rest.exceptions import UnsolvableAnnotationsError
from django_modern_rest.internal.io import identity
from django_modern_rest.metadata import (
    ResponseSpec,
)
from django_modern_rest.negotiation import request_renderer
from django_modern_rest.parsers import Parser
from django_modern_rest.renderers import Renderer
from django_modern_rest.response import build_response
from django_modern_rest.security.base import AsyncAuth, SyncAuth
from django_modern_rest.serializer import BaseSerializer, SerializerContext
from django_modern_rest.settings import HttpSpec
from django_modern_rest.types import (
    infer_type_args,
)
from django_modern_rest.validation import (
    BlueprintValidator,
    ControllerValidator,
)

_SerializerT_co = TypeVar(
    '_SerializerT_co',
    bound=BaseSerializer,
    covariant=True,
)

_ResponseT = TypeVar('_ResponseT', bound=HttpResponse)

_EndpointFunc: TypeAlias = Callable[..., Any]
_Parsers: TypeAlias = Sequence[type[Parser]]
_Renderers: TypeAlias = Sequence[type[Renderer]]


class Blueprint(Generic[_SerializerT_co]):  # noqa: WPS214
    """
    Building block for the API, a collection of named endpoints.

    Use it when you want to compose several endpoints with different
    parsing rules into one final controller.

    It cannot be used directly in routing.
    Before routing, it must be turned into a full-featured controller.

    Attributes:
        endpoint_cls: Class to create endpoints with.
        serializer: Serializer that is passed via type parameters.
            The main goal of the serializer is to serialize object
            to json and deserialize them from json.
            You can't change the serializer simply by modifying
            the attribute in the controller class.
            Because it is already passed to many other places.
            To customize it: create a new class,
            subclass :class:`~django_modern_rest.serializer.BaseSerializer`,
            and pass the new type as a type argument to the controller.
        serializer_context_cls: Class for the input model generation.
            We combine all components like
            :class:`~django_modern_rest.components.Headers`,
            :class:`~django_modern_rest.components.Query`, etc into
            one big model for faster validation and better error messages.
        blueprint_validator_cls: Runs blueprint validation on definition.
        no_validate_http_spec: Set of http spec validation checks
            that we disable for this class.
        validate_responses: Boolean whether or not validating responses.
            Works in runtime, can be disabled for better performance.
        responses: List of responses schemas that this controller can return.
            Also customizable in endpoints and globally with ``'responses'``
            key in the settings.
        http_methods: Set of names to be treated as names for endpoints.
            Does not include ``options``, but includes ``meta``.
        parsers: Sequence of types to be used for this controller
            to parse incoming request's body. All types must be subtypes
            of :class:`~django_modern_rest.parsers.Parser`.
        renderers: Sequence of types to be used for this controller
            to render response's body. All types must be subtypes
            of :class:`~django_modern_rest.renderers.Renderer`.
        auth: Sequence of auth instances to be used for this controller.
            Sync controllers must use instances
            of :class:`django_modern_rest.security.SyncAuth`.
            Async controllers must use instances
            of :class:`django_modern_rest.security.AsyncAuth`.
            Set it to ``None`` to disable auth of this controller.
        error_model: Schema type that represents
            and validates common error responses.
        is_abstract: Whether or not this controller is abstract.
            We consider controller "abstract" when it does not have
            exact serializer type.
        request: Current :class:`~django.http.HttpRequest` instance.
        args: Path positional parameters of the request.
        kwargs: Path named parameters of the request.

    """

    # Public API:
    serializer: ClassVar[type[BaseSerializer]]
    endpoint_cls: ClassVar[type[Endpoint]] = Endpoint
    serializer_context_cls: ClassVar[type[SerializerContext]] = (
        SerializerContext
    )
    blueprint_validator_cls: ClassVar[type[BlueprintValidator]] = (
        BlueprintValidator
    )
    no_validate_http_spec: ClassVar[Set[HttpSpec]] = frozenset()
    validate_responses: ClassVar[bool | None] = None
    responses: ClassVar[Sequence[ResponseSpec]] = []
    http_methods: ClassVar[Set[str]] = frozenset(
        # We replace old existing `View.options` method with modern `meta`:
        {method.name.lower() for method in HTTPMethod} - {'options'} | {'meta'},
    )
    parsers: ClassVar[_Parsers] = ()
    renderers: ClassVar[_Renderers] = ()
    auth: ClassVar[Sequence[SyncAuth] | Sequence[AsyncAuth] | None] = ()
    error_model: ClassVar[Any] = ErrorModel
    is_abstract: ClassVar[bool] = True

    # Instance public API:
    request: HttpRequest
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    __slots__ = ('args', 'kwargs', 'request')

    # Internal API:
    _serializer_context: ClassVar[SerializerContext]
    _component_parsers_builder_cls: ClassVar[type[ComponentParserBuilder]] = (
        ComponentParserBuilder
    )
    _component_parsers: ClassVar[list[ComponentParserSpec]]
    _existing_http_methods: ClassVar[dict[str, _EndpointFunc]]

    @override
    def __init_subclass__(cls) -> None:
        """Build blueprint class from different parts."""
        super().__init_subclass__()
        type_args = infer_type_args(cls, Blueprint)
        if not type_args:
            raise UnsolvableAnnotationsError(
                f'Type args {type_args} are not correct for {cls}, '
                'at least 1 type arg must be provided',
            )
        if isinstance(type_args[0], TypeVar):
            return  # This is a generic subclass of a controller.
        if not issubclass(type_args[0], BaseSerializer):
            raise UnsolvableAnnotationsError(
                f'Type arg {type_args[0]} is not correct for {cls}, '
                'it must be a BaseSerializer subclass',
            )
        cls.is_abstract = False
        cls.serializer = type_args[0]
        cls._component_parsers = cls._component_parsers_builder_cls(
            cls,
            Blueprint,
        )()
        cls._serializer_context = cls.serializer_context_cls(cls)
        cls._existing_http_methods = cls._find_existing_http_methods()
        cls.blueprint_validator_cls()(cls)

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        """
        Set request context.

        Unlike :meth:`~django.views.generic.base.View.setup` does not set
        ``head`` method automatically.

        Thread safety: there's only one blueprint instance per request.
        """
        self.request = request
        self.args = args
        self.kwargs = kwargs

    def to_response(
        self,
        raw_data: Any,
        *,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
        status_code: HTTPStatus | None = None,
        renderer_cls: type[Renderer] | None = None,
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
            renderer_cls=renderer_cls or request_renderer(self.request),
        )

    def to_error(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie | CookieSpec] | None = None,
        renderer_cls: type[Renderer] | None = None,
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
            renderer_cls=renderer_cls or request_renderer(self.request),
        )

    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | None = None,
        error_type: str | ErrorType | None = None,
    ) -> Any:  # `Any`, so we can change the return type in subclasses.
        """
        Convert error to the common format.

        Args:
            error: A serialization exception like a validation error or
                a ``django_modern_rest.exceptions.DataParsingError``.
            loc: Location where this error happened.
                Like "headers" or "field_name".
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

        You can access active blueprint
        via :attr:`~django_modern_rest.controller.Controller.active_blueprint`.
        """
        raise  # noqa: PLE0704

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

        You can access active blueprint
        via :attr:`~django_modern_rest.controller.Controller.active_blueprint`.
        """
        raise  # noqa: PLE0704

    # Protected API:

    @classmethod
    def _find_existing_http_methods(cls) -> dict[str, Callable[..., Any]]:
        """
        Returns what HTTP methods are implemented in this controller.

        Returns both canonical http method name and our dsl name.
        """
        return {
            # Rename `meta` back to `options`:
            ('OPTIONS' if dsl_method == 'meta' else dsl_method.upper()): method
            for dsl_method in cls.http_methods
            if (method := getattr(cls, dsl_method, None)) is not None
        }


#: Type that we expect for a single blueprint composition.
_BlueprintCls: TypeAlias = type[Blueprint[BaseSerializer]]

#: Type for blueprints composition.
_Blueprints: TypeAlias = Sequence[_BlueprintCls]


class Controller(Blueprint[_SerializerT_co], View):  # noqa: WPS214
    """
    Defines API views as controllers.

    Controller is a ``View`` subclass that should be used in the final routing.

    Attributes:
        endpoint_cls: Class to create endpoints with.
        serializer: Serializer that is passed via type parameters.
            The main goal of the serializer is to serialize object
            to json and deserialize them from json.
            You can't change the serializer simply by modifying
            the attribute in the controller class.
            Because it is already passed to many other places.
            To customize it: create a new class,
            subclass :class:`~django_modern_rest.serializer.BaseSerializer`,
            and pass the new type as a type argument to the controller.
        serializer_context_cls: Class for the input model generation.
            We combine all components like
            :class:`~django_modern_rest.components.Headers`,
            :class:`~django_modern_rest.components.Query`, etc into
            one big model for faster validation and better error messages.
        blueprint_validator_cls: Runs blueprint validation on definition.
        controller_validator_cls: Runs full controller validation on definition.
        api_endpoints: Dictionary of HTTPMethod name to controller instance.
        no_validate_http_spec: Set of http spec validation checks
            that we disable for this class.
        validate_responses: Boolean whether or not validating responses.
            Works in runtime, can be disabled for better performance.
        responses: List of responses schemas that this controller can return.
            Also customizable in endpoints and globally with ``'responses'``
            key in the settings.
        http_methods: Set of names to be treated as names for endpoints.
            Does not include ``options``, but includes ``meta``.
        request: Current :class:`~django.http.HttpRequest` instance.
        args: Path positional parameters of the request.
        kwargs: Path named parameters of the request.
        blueprints: A sequence of :class:`Blueprint` types
            that should be composed together.

    """

    # Public class-level API:
    blueprints: ClassVar[_Blueprints] = ()
    controller_validator_cls: ClassVar[type[ControllerValidator]] = (
        ControllerValidator
    )
    api_endpoints: ClassVar[Mapping[str, Endpoint]]

    # Public instance API:
    blueprint: Blueprint[_SerializerT_co] | None

    # Protected API:
    _blueprint_per_method: ClassVar[Mapping[str, _BlueprintCls]]
    _is_async: ClassVar[bool | None] = None  # `None` means that nothing's found

    @override
    def __init_subclass__(cls) -> None:
        """Collect blueprints if they exist."""
        super().__init_subclass__()
        if getattr(cls, 'serializer', None) is None:
            return  # This is a generic controller

        # Now it is validated that we don't have intersections.
        cls.api_endpoints = {
            canonical: cls.endpoint_cls(
                meth,
                blueprint_cls=None,
                controller_cls=cls,
            )
            for canonical, meth in cls._existing_http_methods.items()
        }
        cls.api_endpoints.update({
            canonical: cls.endpoint_cls(
                meth,
                blueprint_cls=blueprint_cls,
                controller_cls=cls,
            )
            for blueprint_cls in cls.blueprints
            for canonical, meth in blueprint_cls._existing_http_methods.items()  # noqa: SLF001
        })
        cls._blueprint_per_method = {
            canonical: blueprint
            for blueprint in cls.blueprints
            for canonical in blueprint._existing_http_methods  # noqa: SLF001
        }
        cls._is_async = cls.controller_validator_cls()(cls)

    @override
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        """
        Set up common attributes.

        Thread safety: there's only one controller instance per request.
        """
        super().setup(request, *args, **kwargs)
        # Controller is created once per request, so we can assign attributes.
        blueprint = self._blueprint_per_method.get(  # pyrefly: ignore[no-matching-overload]  # noqa: E501
            request.method,  # type: ignore[arg-type]
        )
        if blueprint:
            instance = blueprint()
            instance.setup(request, *args, **kwargs)
            # We validate that serializers match during import time:
            self.blueprint = instance  # type: ignore[assignment]
        else:
            self.blueprint = None

    @override
    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Find an endpoint that serves this HTTP method and call it.

        Return 405 if this method is not allowed.
        """
        # Fast path for method resolution:
        method: str = request.method  # type: ignore[assignment]
        endpoint = self.api_endpoints.get(method)
        if endpoint is not None:
            # TODO: support `StreamingHttpResponse`
            # TODO: support `FileResponse`
            # TODO: support redirects
            return endpoint(self, *args, **kwargs)
        # This return is very special,
        # since it does not have an attached endpoint.
        # All other responses are handled on endpoint level
        # with all the response type validation.
        return self.handle_method_not_allowed(method)

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
                >>> from django_modern_rest import Controller, validate
                >>> from django_modern_rest.plugins.pydantic import (
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
           ...             method.upper() for method in self.http_methods
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

               >>> from django_modern_rest.options_mixins import MetaMixin

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
                    (
                        f'Method {method!r} is not allowed, '
                        f'allowed: {allowed_methods!r}'
                    ),
                    error_type=ErrorType.not_allowed,
                ),
                status_code=HTTPStatus.METHOD_NOT_ALLOWED,
                renderer_cls=request_renderer(self.request),
            ),
        )

    @classproperty
    @override
    def view_is_async(cls) -> bool:  # noqa: N805  # pyright: ignore[reportIncompatibleVariableOverride]  # pyrefly: ignore[bad-override]
        """We already know this in advance, no need to recalculate."""
        return cls._is_async is True

    @cached_property
    def active_blueprint(self) -> Blueprint[_SerializerT_co]:
        """Returns a blueprint if it was used, otherwise, returns self."""
        return self.blueprint or self

    # Protected API:

    @classmethod
    def _maybe_wrap(
        cls,
        response: _ResponseT,
    ) -> _ResponseT:
        """Wraps response into a coroutine if this is an async controller."""
        if cls._is_async:
            return identity(response)
        return response
