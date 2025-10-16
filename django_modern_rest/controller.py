from http import HTTPStatus
from typing import Any, ClassVar, Generic, TypeAlias, TypeVar, get_args

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse
from django.utils.functional import classproperty
from django.views import View
from typing_extensions import override

from django_modern_rest.components import ComponentParserMixin
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import (
    MethodNotAllowedError,
    SerializationError,
    UnsolvableAnnotationsError,
)
from django_modern_rest.serialization import BaseSerializer, SerializerContext
from django_modern_rest.types import (
    Empty,
    EmptyObj,
    infer_bases,
    infer_type_args,
)

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)

_ComponentParserSpec: TypeAlias = list[type[ComponentParserMixin],]


class Controller(View, Generic[_SerializerT]):
    """Defines API views as controllers."""

    # Public API:
    endpoint_cls: ClassVar[type[Endpoint]] = Endpoint

    # We lie about that it is an instance variable, because type vars
    # are not allowed in `ClassVar`:
    _serializer: type[BaseSerializer]

    # Internal API:
    _component_parsers: ClassVar[_ComponentParserSpec]
    _api_endpoints: ClassVar[dict[str, Endpoint]]
    _current_endpoint: Endpoint
    _combined_model_cache: ClassVar[type[Any] | None] = None
    _serializer_context: ClassVar[SerializerContext]

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
        cls._component_parsers = list(infer_bases(cls, ComponentParserMixin))
        cls._api_endpoints = {
            meth: cls.endpoint_cls(func, serializer=cls._serializer)
            for meth in cls.existing_http_methods
            if (func := getattr(cls, meth)) is not getattr(View, meth, None)
        }
        cls._validate_endpoints()
        cls._combined_model_cache = cls._create_combined_model()

        cls._serializer_context = SerializerContext(
            cls._component_parsers,
            cls._serializer,
            combined_model=cls._combined_model_cache,
        )

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
            return self._handle_error(exc)
        except MethodNotAllowedError:
            return self.http_method_not_allowed(request, *args, **kwargs)

    @classproperty  # TODO: cache
    def existing_http_methods(cls) -> set[str]:  # noqa: N805
        """Returns and caches what HTTP methods are implemented in this view."""
        return {
            method
            for method in cls.http_method_names
            if getattr(cls, method, None) is not None
        }

    # Private API:

    @classmethod
    def _create_combined_model(cls) -> type[Any]:
        specs = {}
        for component in cls._component_parsers:
            type_args = get_args(component)
            if type_args:
                name = component._provide_context_name()  # noqa: SLF001
                specs[name] = type_args[0]

        return cls._serializer.create_combined_model(specs)

    @classmethod
    def _validate_endpoints(cls) -> None:
        """Validate that endpoints definition is correct in build time."""
        if not cls._api_endpoints:
            return
        is_async = cls._api_endpoints[
            next(iter(cls._api_endpoints.keys()))
        ].is_async
        if any(
            endpoint.is_async is not is_async
            for endpoint in cls._api_endpoints.values()
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
        endpoint = self._api_endpoints.get(request.method.lower())  # type: ignore[union-attr]
        if endpoint is not None:
            self._current_endpoint = endpoint
            # TODO: support `StreamingHttpResponse`
            # TODO: support `JsonResponse`
            # TODO: use `return_type` for schema generation
            # TODO: use configurable `json` encoders and decoders
            # TODO: make sure `return_dto` validation
            # can be turned off for production
            self._validate_components(request, *args, **kwargs)
            return endpoint(self, *args, **kwargs)  # we don't pass request
        raise MethodNotAllowedError

    def _validate_components(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        validated_data = self._serializer_context.collect_and_parse(
            request,
            *args,
            **kwargs,
        )

        for attr_name, attr_value in validated_data.items():
            setattr(self, attr_name, attr_value)

    def _handle_error(self, exc: SerializationError) -> HttpResponse:
        payload = {'detail': exc.args[0]}
        return HttpResponse(
            self._serializer.to_json(payload),
            status=int(exc.status_code),
            content_type='application/json',
        )
