from collections.abc import Mapping
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
from django.utils.functional import cached_property, classproperty
from django.views import View
from typing_extensions import deprecated, override

from django_modern_rest.components import ComponentParser
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import (
    MethodNotAllowedError,
    UnsolvableAnnotationsError,
)
from django_modern_rest.internal.io import identity
from django_modern_rest.response import ResponseDescription, build_response
from django_modern_rest.serialization import BaseSerializer, SerializerContext
from django_modern_rest.settings import (
    DMR_GLOBAL_ERROR_HANDLER_KEY,
    resolve_setting,
)
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
        serializer_context_cls: Class for the input model generation.
            We combine all components like ``Headers``, ``Query``, etc into
            one big model for faster validation and better error messages.
        controller_validator_cls: Runs controller validation on definition.
        api_endpoints: Dictionary of HTTPMethod name to controller instance.
        validate_responses: Boolean whether or not validating responses.
            Works in runtime, can be disabled for better performance.
        responses: List of responses schemas that this controller can return.
            Also customizable in endpoints and globally.

    """

    # Public API:
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

    # We lie about that it is an instance variable, because type vars
    # are not allowed in `ClassVar`, can be accessed in runtype via class:
    serializer: type[BaseSerializer]

    # Internal API:
    _component_parsers: ClassVar[list[_ComponentParserSpec]]
    _is_async: ClassVar[bool]
    _serializer_context: ClassVar[Any]

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
        cls.serializer = type_args[0]
        cls._component_parsers = [
            (subclass, get_args(subclass))
            for subclass in infer_bases(cls, ComponentParser)
        ]
        cls._serializer_context = cls.serializer_context_cls(cls)
        cls.api_endpoints = {
            meth: cls.endpoint_cls(func, serializer=cls.serializer)
            for meth in cls.existing_http_methods()
            if (func := getattr(cls, meth)) is not getattr(View, meth, None)
        }
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

    def handle_error(self, exc: Exception) -> HttpResponse:
        """Return error response."""
        return resolve_setting(  # type: ignore[no-any-return]
            DMR_GLOBAL_ERROR_HANDLER_KEY,
            import_string=True,
        )(self, exc)

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
        except MethodNotAllowedError as exc:
            # This exception is very special,
            # since it does not have an attached endpoint.
            return self.handle_method_not_allowed(exc.method)
        except Exception as exc:
            return self._maybe_wrap(self.handle_error(exc))

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
        return {
            method
            for method in cls.http_method_names
            if getattr(cls, method, None) is not None
        }

    @cached_property
    def response_map(self) -> Mapping[HTTPStatus, ResponseDescription]:
        """Returns and caches the responses as a map."""
        return {response.status_code: response for response in self.responses}

    @classproperty
    @override
    def view_is_async(cls) -> bool:  # noqa: N805  # pyright: ignore[reportIncompatibleVariableOverride]
        """We already know this in advance, no need to recalculate."""
        return cls._is_async

    # Private API:

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
            # TODO: support redirects
            self._serializer_context.parse_and_bind(
                self,
                request,
                *args,
                **kwargs,
            )
            return endpoint(self, *args, **kwargs)  # we don't pass request
        raise MethodNotAllowedError(method)

    @classmethod
    def _maybe_wrap(
        cls,
        response: _ResponseT,
    ) -> _ResponseT:
        """Wraps response into a coroutine if this is an async controller."""
        if cls.view_is_async:
            return identity(response)
        return response
