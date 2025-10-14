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


class ComponentParserMixin:
    """Base abtract parser for request components."""

    __is_base_type__: ClassVar[bool] = True

    @classmethod
    @abc.abstractmethod
    def _extract_raw_data(
        cls,
        request: HttpRequest,
        serializer: type[BaseSerializer],
    ) -> Any:
        """Extract raw data from request without validation."""
        raise NotImplementedError

    @abc.abstractmethod
    def _parse_component(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        raise NotImplementedError


class Query(ComponentParserMixin, Generic[_QueryT]):
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

    @classmethod
    @override
    def _extract_raw_data(
        cls,
        request: HttpRequest,
        serializer: type[BaseSerializer],
    ) -> Any:
        return request.GET  # Просто возвращаем данные

    @override
    def _parse_component(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # TODO: validate `type_args` len
        try:
            self.parsed_query = serializer.from_python(
                request.GET,
                type_args[0],
            )
        except serializer.validation_error as exc:
            raise RequestSerializationError(
                serializer.error_to_json(exc),
            ) from None


class Body(ComponentParserMixin, Generic[_BodyT]):
    """
    Parses body of the request.

    # TODO: example

    If your controller class inherits from ``Body`` - then you can access
    parsed body as ``self.parsed_body`` attribute.
    """

    parsed_body: _BodyT

    @classmethod
    @override
    def _extract_raw_data(
        cls,
        request: HttpRequest,
        serializer: type[BaseSerializer],
    ) -> Any:
        try:
            return serializer.from_json(request.body)
        except (msgspec.DecodeError, TypeError) as exc:
            raise RequestSerializationError(str(exc)) from None

    @override
    def _parse_component(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # TODO: negotiate content-type
        # TODO: make default encoding configurable
        try:
            self.parsed_body = serializer.from_python(
                serializer.from_json(request.body),
                type_args[0],
            )
        except (msgspec.DecodeError, TypeError) as exc:
            raise RequestSerializationError(str(exc)) from exc
        except serializer.validation_error as exc:
            raise RequestSerializationError(
                serializer.error_to_json(exc),
            ) from None


class Headers(ComponentParserMixin, Generic[_HeadersT]):
    """
    Parses request headers.

    # TODO: example

    If your controller class inherits from ``Headers`` - then you can access
    parsed headers as ``self.parsed_headers`` attribute.
    """

    parsed_headers: _HeadersT

    @classmethod
    @override
    def _extract_raw_data(
        cls,
        request: HttpRequest,
        serializer: type[BaseSerializer],
    ) -> Any:
        return request.headers

    @override
    def _parse_component(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # TODO: validate `type_args` len
        try:
            self.parsed_headers = serializer.from_python(
                request.headers,
                type_args[0],
            )
        except serializer.validation_error as exc:
            raise RequestSerializationError(
                serializer.error_to_json(exc),
            ) from None
