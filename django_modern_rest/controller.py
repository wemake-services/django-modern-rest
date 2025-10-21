from http import HTTPStatus
from typing import (
    Any,
    ClassVar,
    Generic,
    TypeAlias,
    TypeVar,
    get_args,
)

from django.http import HttpRequest, HttpResponse
from django.utils.functional import classproperty
from django.views import View
from typing_extensions import deprecated, override

from django_modern_rest.components import ComponentParser
from django_modern_rest.endpoint import Endpoint, validate
from django_modern_rest.exceptions import (
    UnsolvableAnnotationsError,
)
from django_modern_rest.headers import HeaderDescription
from django_modern_rest.internal.io import identity
from django_modern_rest.response import ResponseDescription, build_response
from django_modern_rest.serialization import BaseSerializer, SerializerContext
from django_modern_rest.types import (
    Empty,
    EmptyObj,
    infer_bases,
    infer_type_args,
)
from django_modern_rest.validation import ControllerValidator

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


class Controller(View, Generic[_SerializerT_co]):  # noqa: WPS214
    """
    Defines API views as controllers.

    Attrs:
        endpoint_cls: Class to create endpoints with.
        serializer: Serializer that is passed via type parameters.
            The main goal of the serializer is to serialize object
            to json and deserialize them from json.
            You can't change the serializer simply by modifying
            the attribute in the controller class.
            Because it is already passed to many other places.
            To customize it: create a new class, pass the serializer
            type as a type argument to the controller.
        serializer_context_cls: Class for the input model generation.
            We combine all components like ``Headers``, ``Query``, etc into
            one big model for faster validation and better error messages.
        controller_validator_cls: Runs controller validation on definition.
        api_endpoints: Dictionary of HTTPMethod name to controller instance.
        validate_responses: Boolean whether or not validating responses.
            Works in runtime, can be disabled for better performance.
        responses: List of responses schemas that this controller can return.
            Also customizable in endpoints and globally with ``'responses'``
            key in the settings.

    """

    # Public API:
    serializer: ClassVar[type[BaseSerializer]]
    serializer_context: ClassVar[SerializerContext]
    endpoint_cls: ClassVar[type[Endpoint]] = Endpoint
    serializer_context_cls: ClassVar[type[SerializerContext]] = (
        SerializerContext
    )
    controller_validator_cls: ClassVar[type[ControllerValidator]] = (
        ControllerValidator
    )
    api_endpoints: ClassVar[dict[str, Endpoint]]
    validate_responses: ClassVar[bool | Empty] = EmptyObj
    responses: ClassVar[list[ResponseDescription]] = []
    responses_from_components: ClassVar[bool] = True

    # Internal API:
    _component_parsers: ClassVar[list[_ComponentParserSpec]]
    _is_async: ClassVar[bool]

    @override
    def __init_subclass__(cls) -> None:  # noqa: C901
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
                f'Type arg {type_args[0]} is not correct for {cls}, '
                'it must be a BaseSerializer subclass',
            )
        cls.serializer = type_args[0]
        cls._component_parsers = [
            (subclass, get_args(subclass))
            for subclass in infer_bases(cls, ComponentParser)
        ]
        cls.serializer_context = cls.serializer_context_cls(cls)

        # Build API endpoints
        api_endpoints = {}
        for meth in cls.existing_http_methods():
            func = getattr(cls, meth, None)
            if func is not None and func is not getattr(View, meth, None):
                # Skip our deprecated options method
                if meth == 'options' and func is cls.options:
                    continue
                api_endpoints[meth] = cls.endpoint_cls(func, controller_cls=cls)

        # Special handling for meta method -> options mapping
        meta_func = getattr(cls, 'meta', None)
        if meta_func is not None:
            api_endpoints['options'] = cls.endpoint_cls(
                meta_func, controller_cls=cls,
            )
        else:
            # Default OPTIONS handler when no meta method is defined
            @validate(
                ResponseDescription(
                    None,
                    status_code=HTTPStatus.NO_CONTENT,
                    headers={'Allow': HeaderDescription()},
                ),
            )
            def default_options_wrapper(self: Controller[_SerializerT_co]) -> HttpResponse:
                return cls._default_options_handler()

            api_endpoints['options'] = cls.endpoint_cls(
                default_options_wrapper, controller_cls=cls,
            )

        cls.api_endpoints = api_endpoints
        cls._is_async = cls.controller_validator_cls()(cls)

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
            self.serializer,
            raw_data=raw_data,
            headers=headers,
            status_code=status_code,
        )

    def to_error(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus,
        headers: dict[str, str] | Empty = EmptyObj,
    ) -> HttpResponse:
        """
        Helpful method to convert API error parts into an actual response.

        Should be always used instead of using
        raw :class:`django.http.HttpResponse` objects.
        Does the usual response and error response validation.
        """
        return build_response(
            None,
            self.serializer,
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
        """
        Find an endpoint that serves this HTTP method and call it.

        Return 405 if this method is not allowed.
        """
        # Fast path for method resolution:
        method = request.method.lower()  # type: ignore[union-attr]
        endpoint = self.api_endpoints.get(method)
        if endpoint is not None:
            # TODO: support `StreamingHttpResponse`
            # TODO: support `FileResponse`
            # TODO: support redirects
            return endpoint(self, *args, **kwargs)  # we don't pass request
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
        'use `meta` method instead',
    )
    def options(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Do not use, use `meta` method instead.

        Django's `View.options` has incompatible signature with
        django-modern-rest.
        Use `meta` method for OPTIONS handling.
        """
        raise NotImplementedError(
            'Please do not use `options` method with `django-modern-rest`, '
            'use `meta` method instead',
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
        return cls._maybe_wrap(
            build_response(
                None,
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

    @classmethod
    def existing_http_methods(cls) -> set[str]:
        """Returns and caches what HTTP methods are implemented in this view."""
        methods = {
            method
            for method in cls.http_method_names
            if getattr(cls, method, None) is not None
        }

        # Always include options (either custom meta method or default handler)
        methods.add('options')

        return methods

    @classmethod
    @validate(ResponseDescription(None, status_code=HTTPStatus.NO_CONTENT))
    def _default_options_handler(cls) -> HttpResponse:
        """Default OPTIONS handler that returns Allow header."""
        allowed_methods = sorted(
            method.upper()
            for method in cls.existing_http_methods()
        )
        return cls._maybe_wrap(
            build_response(
                None,
                cls.serializer,
                raw_data=None,
                status_code=HTTPStatus.NO_CONTENT,
                headers={'Allow': ', '.join(allowed_methods)},
            ),
        )

    @classmethod
    def semantic_responses(cls) -> list[ResponseDescription]:
        """
        Returns all user-defined and component-defined responses.

        Optionally component-defined responses can be turned off with falsy
        :attr:`responses_from_components` attribute on a controller.
        We call it once per endpoint creation.
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

    @classproperty
    @override
    def view_is_async(cls) -> bool:  # noqa: N805  # pyright: ignore[reportIncompatibleVariableOverride]
        """We already know this in advance, no need to recalculate."""
        return cls._is_async

    @classmethod
    def _maybe_wrap(
        cls,
        response: _ResponseT,
    ) -> _ResponseT:
        """Wraps response into a coroutine if this is an async controller."""
        if cls.view_is_async:
            return identity(response)
        return response
