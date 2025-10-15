import abc
from typing import Any, ClassVar, Generic, TypeVar

import msgspec
from django.http import HttpRequest
from typing_extensions import override

from django_modern_rest.exceptions import RequestSerializationError
from django_modern_rest.serialization import BaseSerializer

_QueryT = TypeVar('_QueryT')
_BodyT = TypeVar('_BodyT')
_HeadersT = TypeVar('_HeadersT')


class ComponentParser:
    """Base abtract parser for request components."""

    # Public API:
    strict_validation: ClassVar[bool] = False

    # Internal API:
    __is_base_type__: ClassVar[bool] = True

    @abc.abstractmethod
    def parse_component(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Implement this method to be able to parse any request component."""
        raise NotImplementedError


class Query(ComponentParser, Generic[_QueryT]):
    """
    Parses query params of the request.

    For example:

    .. code:: python

       >>> import pydantic

       >>> class Ordering(pydantic.BaseModel):
       ...     ordering: str
       ...     reversed: bool

    Will parse a request like ``?ordering=price&reversed=true``
    into ``Ordering`` model.

    If your controller class inherits from ``Query`` - then you can access
    parsed query model as ``self.parsed_query`` attribute.
    """

    parsed_query: _QueryT

    @override
    def parse_component(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Parses query strings from request."""
        # TODO: validate `type_args` len
        try:
            self.parsed_query = serializer.from_python(
                request.GET,
                type_args[0],
                strict=self.strict_validation,
            )
        except serializer.validation_error as exc:
            raise RequestSerializationError(
                serializer.error_to_json(exc),
            ) from None


class Body(ComponentParser, Generic[_BodyT]):
    """
    Parses body of the request.

    # TODO: example

    If your controller class inherits from ``Body`` - then you can access
    parsed body as ``self.parsed_body`` attribute.
    """

    parsed_body: _BodyT

    @override
    def parse_component(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Parses request body."""
        if request.content_type != serializer.content_type:
            raise RequestSerializationError(
                'Cannot parse request body '
                f'with content type {request.content_type!r}, '
                f'expected {serializer.content_type!r}',
            )
        try:
            self.parsed_body = serializer.from_python(
                serializer.from_json(request.body),
                type_args[0],
                strict=self.strict_validation,
            )
        except (msgspec.DecodeError, TypeError) as exc:
            raise RequestSerializationError(str(exc)) from exc
        except serializer.validation_error as exc:
            raise RequestSerializationError(
                serializer.error_to_json(exc),
            ) from None


class Headers(ComponentParser, Generic[_HeadersT]):
    """
    Parses request headers.

    # TODO: example

    If your controller class inherits from ``Headers`` - then you can access
    parsed headers as ``self.parsed_headers`` attribute.
    """

    parsed_headers: _HeadersT

    @override
    def parse_component(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Parses request headers."""
        # TODO: validate `type_args` len
        try:
            self.parsed_headers = serializer.from_python(
                request.headers,
                type_args[0],
                strict=self.strict_validation,
            )
        except serializer.validation_error as exc:
            raise RequestSerializationError(
                serializer.error_to_json(exc),
            ) from None
