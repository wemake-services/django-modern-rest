from collections.abc import Mapping, Sequence
from http import HTTPMethod, HTTPStatus
from typing import (
    Any,
    ClassVar,
    Generic,
    TypeAlias,
    TypeVar,
    get_args,
)

from django.http import HttpRequest, HttpResponse
from django.utils.functional import cached_property, classproperty
from django.views import View
from typing_extensions import deprecated, override

from django_modern_rest.components import ComponentParser
from django_modern_rest.cookies import NewCookie
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import (
    UnsolvableAnnotationsError,
)
from django_modern_rest.internal.io import identity
from django_modern_rest.response import (
    ResponseSpec,
    build_response,
)
from django_modern_rest.serialization import BaseSerializer, SerializerContext
from django_modern_rest.types import (
    infer_bases,
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

_ComponentParserSpec: TypeAlias = tuple[
    type[ComponentParser],
    tuple[Any, ...],
]


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
            subclass :class:`~django_modern_rest.serialization.BaseSerializer`,
            and pass the new type as a type argument to the controller.
        serializer_context_cls: Class for the input model generation.
            We combine all components like
            :class:`~django_modern_rest.components.Headers`,
            :class:`~django_modern_rest.components.Query`, etc into
            one big model for faster validation and better error messages.
        validator_cls: Runs controller validation on definition.
        api_endpoints: Dictionary of HTTPMethod name to controller instance.
        validate_responses: Boolean whether or not validating responses.
            Works in runtime, can be disabled for better performance.
        responses: List of responses schemas that this controller can return.
            Also customizable in endpoints and globally with ``'responses'``
            key in the settings.
        responses_from_components: Should we automatically add response schemas
            from components like :class:`django_modern_rest.components.Headers`
            into the :attr:`responses`?
        http_methods: Set of names to be treated as names for endpoints.
            Does not include ``options``, but includes ``meta``.
        request: Current :class:`~django.http.HttpRequest` instance.
        args: Path positional parameters of the request.
        kwargs: Path named parameters of the request.

    """

    # Public API:
    serializer: ClassVar[type[BaseSerializer]]
    serializer_context: ClassVar[SerializerContext]
    endpoint_cls: ClassVar[type[Endpoint]] = Endpoint
    serializer_context_cls: ClassVar[type[SerializerContext]] = (
        SerializerContext
    )
    validator_cls: ClassVar[type[BlueprintValidator]] = BlueprintValidator
    # str and not HTTPMethod, because of `meta` method:
    api_endpoints: ClassVar[dict[str, Endpoint]]
    validate_responses: ClassVar[bool | None] = None
    responses: ClassVar[list[ResponseSpec]] = []
    responses_from_components: ClassVar[bool] = True
    http_methods: ClassVar[frozenset[str]] = frozenset(
        # We replace old existing `View.options` method with modern `meta`:
        {method.name.lower() for method in HTTPMethod} - {'options'} | {'meta'},
    )

    # Instance public API:
    request: HttpRequest
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    __slots__ = ('args', 'kwargs', 'request')

    # Internal API:
    _component_parsers: ClassVar[list[_ComponentParserSpec]]
    _is_async: ClassVar[bool]

    @override
    def __init_subclass__(
        cls,
        *,
        controller_cls: type['Controller[BaseSerializer]'] | None = None,
    ) -> None:
        """Build blueprint class from different parts."""
        super().__init_subclass__()
        type_args = infer_type_args(cls, Blueprint)
        if len(type_args) != 1:
            raise UnsolvableAnnotationsError(
                f'Type args {type_args} are not correct for {cls}, '
                'only 1 type arg must be provided',
            )
        if isinstance(type_args[0], TypeVar):
            return  # This is a generic subclass of a controller.
        if not issubclass(type_args[0], BaseSerializer):
            raise UnsolvableAnnotationsError(
                f'Type arg {type_args[0]} is not correct for {cls}, '
                'it must be a BaseSerializer subclass',
            )
        cls.serializer = type_args[0]
        cls._component_parsers = [
            (subclass, get_args(subclass))
            for subclass in infer_bases(cls, ComponentParser)
        ]
        cls.serializer_context = cls.serializer_context_cls(cls)
        if getattr(cls, 'api_endpoints', None) is None:
            cls.api_endpoints = {}
        cls.api_endpoints.update({
            canonical: cls.endpoint_cls(
                getattr(cls, dsl),
                blueprint_cls=cls,
                controller_cls=controller_cls,
            )
            for canonical, dsl in cls.existing_http_methods()
        })
        cls._is_async = cls.validator_cls()(cls)

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
        headers: dict[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        status_code: HTTPStatus | None = None,
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
        )

    def to_error(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus,
        headers: dict[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
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
        )

    def handle_error(self, endpoint: Endpoint, exc: Exception) -> HttpResponse:
        """
        Return error response if possible. Sync case.

        Override this method to add custom error handling for sync execution.
        By default - does nothing, only re-raises the passed error.
        Won't be called when using async endpoints.
        """
        raise exc

    async def handle_async_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        """
        Return error response if possible. Async case.

        Override this method to add custom error handling for async execution.
        By default - does nothing, only re-raises the passed error.
        Won't be called when using sync endpoints.
        """
        raise exc

    @classmethod
    def existing_http_methods(cls) -> set[tuple[str, str]]:
        """
        Returns what HTTP methods are implemented in this view.

        Returns both canonical http method name and our dsl name.
        """
        return {
            # Rename `meta` back to `options`:
            (
                'OPTIONS' if dsl_method == 'meta' else dsl_method.upper(),
                dsl_method,
            )
            for dsl_method in cls.http_methods
            if getattr(cls, dsl_method, None) is not None
        }

    @classmethod
    def semantic_responses(cls) -> list[ResponseSpec]:
        """
        Returns all user-defined responses in layers above endpoint itself.

        Optionally responses can be turned off with falsy
        :attr:`responses_from_components` attribute
        on a blueprint or a controller.
        We call it once per blueprint
        and once per controller when creating endpoint.
        """
        if not cls.responses_from_components:
            return cls.responses

        # Get the responses that were provided by the user.
        existing_codes = {response.status_code for response in cls.responses}
        extra_responses = [
            response
            for component, model in cls._component_parsers
            for response in component.provide_responses(
                cls.serializer,
                model,
            )
            # If some response already exists, do not override it.
            if response.status_code not in existing_codes
        ]
        return [*cls.responses, *set(extra_responses)]

    # Private API:

    @classmethod
    def _maybe_wrap(
        cls,
        response: _ResponseT,
    ) -> _ResponseT:
        """Wraps response into a coroutine if this is an async controller."""
        if cls._is_async:
            return identity(response)
        return response


#: Type that we expect for a single blueprint composition.
_BlueprintT: TypeAlias = type[Blueprint[BaseSerializer]]

#: Type for blueprints composition.
BlueprintsT: TypeAlias = Sequence[_BlueprintT]


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
            subclass :class:`~django_modern_rest.serialization.BaseSerializer`,
            and pass the new type as a type argument to the controller.
        serializer_context_cls: Class for the input model generation.
            We combine all components like
            :class:`~django_modern_rest.components.Headers`,
            :class:`~django_modern_rest.components.Query`, etc into
            one big model for faster validation and better error messages.
        validator_cls: Runs controller validation on definition.
        api_endpoints: Dictionary of HTTPMethod name to controller instance.
        validate_responses: Boolean whether or not validating responses.
            Works in runtime, can be disabled for better performance.
        responses: List of responses schemas that this controller can return.
            Also customizable in endpoints and globally with ``'responses'``
            key in the settings.
        responses_from_components: Should we automatically add response schemas
            from components like :class:`django_modern_rest.components.Headers`
            into the :attr:`responses`?
        http_methods: Set of names to be treated as names for endpoints.
            Does not include ``options``, but includes ``meta``.
        request: Current :class:`~django.http.HttpRequest` instance.
        args: Path positional parameters of the request.
        kwargs: Path named parameters of the request.
        blueprints: A sequence of :class:`Blueprint` types
            that should be composed together.

    """

    # Public class-level API:
    blueprints: ClassVar[BlueprintsT]
    validator_cls: ClassVar[type[BlueprintValidator]] = ControllerValidator

    # Public instance API:
    blueprint: Blueprint[_SerializerT_co] | None

    # Protected API:
    _blueprint_per_method: ClassVar[Mapping[str, _BlueprintT]]

    @override
    def __init_subclass__(cls) -> None:
        """Collect blueprints if they exist."""
        cls.blueprints = getattr(cls, 'blueprints', [])
        cls.api_endpoints = {}  # will be re-populated in the very end
        for blueprint in cls.blueprints:
            cls.api_endpoints.update(blueprint.api_endpoints)
        super().__init_subclass__(controller_cls=cls)
        # It is validated that we don't have intersections.
        cls._blueprint_per_method = {
            # TODO: this violation is a bug in WPS
            canonical: blueprint  # noqa: WPS441
            for blueprint in cls.blueprints
            for canonical, _dsl in blueprint.existing_http_methods()  # noqa: WPS441
        }

    @override
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        """
        Set up common attributes.

        Thread safety: there's only one controller instance per request.
        """
        super().setup(request, *args, **kwargs)
        # Controller is created once per request, so we can assign attributes.
        blueprint = self._blueprint_per_method.get(
            request.method,  # type: ignore[arg-type]
        )
        if blueprint:
            instance = blueprint()
            instance.setup(request, *args, **kwargs)
            # We validate that serializers match:
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
        allowed_methods = sorted(cls.api_endpoints.keys())
        return cls._maybe_wrap(
            build_response(
                cls.serializer,
                raw_data={
                    'detail': (
                        f'Method {method!r} is not allowed, '
                        f'allowed: {allowed_methods!r}'
                    ),
                },
                status_code=HTTPStatus.METHOD_NOT_ALLOWED,
            ),
        )

    @classproperty
    @override
    def view_is_async(cls) -> bool:  # noqa: N805  # pyright: ignore[reportIncompatibleVariableOverride]
        """We already know this in advance, no need to recalculate."""
        return cls._is_async

    @cached_property
    def active_blueprint(self) -> Blueprint[_SerializerT_co]:
        """Returns a blueprint if it was used, otherwise, returns self."""
        return self.blueprint or self
