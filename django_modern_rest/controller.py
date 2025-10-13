from typing import Any, ClassVar, Generic, TypeAlias, TypeVar, get_args

from django.http import HttpRequest, HttpResponse
from django.utils.functional import classproperty
from django.views import View
from typing_extensions import override

from django_modern_rest.components import ComponentParserMixin
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import (
    SerializationError,
    UnsolvableAnnotationsError,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import infer_bases, infer_type_args

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)

_ComponentParserSpec: TypeAlias = tuple[
    type[ComponentParserMixin],
    tuple[Any, ...],
]


class Controller(View, Generic[_SerializerT]):
    """Defines API views as controllers."""

    # We lie about that it is an instance variable, because type vars
    # are not allowed in `ClassVar`:
    _serializer: type[BaseSerializer]

    # Internal API:
    _component_parsers: ClassVar[list[_ComponentParserSpec]]
    _api_endpoints: ClassVar[dict[str, Endpoint]]

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

        if getattr(cls, '_component_parsers', None) is None:
            cls._component_parsers = [
                (subclass, get_args(subclass))
                for subclass in infer_bases(cls, ComponentParserMixin)
            ]

        if getattr(cls, '_api_endpoints', None) is None:
            cls._api_endpoints = {
                meth: Endpoint(func, serializer=cls._serializer)
                for meth in cls.existing_http_methods
                if (func := getattr(cls, meth)) is not getattr(View, meth, None)
            }

    @override
    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Parse all components before the dispatching and call controller."""
        try:
            response = self._handle_request(request, *args, **kwargs)
        except SerializationError as exc:
            return self._handle_error(exc)
        else:
            if response is not None:
                return response
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

    # Private API:

    def _handle_request(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse | None:
        # Fast path for method resolution:
        endpoint = self._api_endpoints.get(request.method.lower())  # type: ignore[union-attr]
        if endpoint is not None:
            # TODO: validate `HttpResponse.content` with `return_type`
            # TODO: support `StreamingHttpResponse`
            # TODO: support `JsonResponse`
            # TODO: use `return_type` for schema generation
            # TODO: use configurable `json` encoders and decoders
            # TODO: make sure `return_dto` validation
            # can be turned off for production
            for parser, type_args in self._component_parsers:
                # TODO: maybe parse all at once?
                # See https://github.com/wemake-services/django-modern-rest/issues/8
                parser._parse_component(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    # We lie that this is a `ComponentParserMixin`, but their
                    # APIs are compatible by design.
                    self,  # type: ignore[arg-type]
                    self._serializer,
                    type_args,
                    request,
                    *args,
                    **kwargs,
                )
            return endpoint(self, *args, **kwargs)  # we don't pass request
        return None

    def _handle_error(self, exc: SerializationError) -> HttpResponse:
        payload = {'detail': str(exc)}
        return HttpResponse(
            self._serializer.to_json(payload),
            status=int(exc.status_code),
        )
