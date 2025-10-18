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
    """Base abstract provider for request components."""

    # Public API:
    strict_validation: ClassVar[bool] = False

    # Internal API:
    __is_base_type__: ClassVar[bool] = True

    @classmethod
    @abc.abstractmethod
    def _provide_context_name(cls) -> str:
        """Attribute name to bind parsed data to (e.g. 'parsed_body')."""
        raise NotImplementedError

    @abc.abstractmethod
    def _provide_context_data(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Return unstructured raw value for serializer.from_python().

        Implement body JSON decoding / content-type checks here if needed.
        """
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

    @classmethod
    @override
    def _provide_context_name(cls) -> str:
        return 'parsed_query'

    @override
    def _provide_context_data(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return request.GET


class Body(ComponentParser, Generic[_BodyT]):
    """
    Parses body of the request.

    # TODO: example

    If your controller class inherits from ``Body`` - then you can access
    parsed body as ``self.parsed_body`` attribute.
    """

    parsed_body: _BodyT

    @classmethod
    @override
    def _provide_context_name(cls) -> str:
        return 'parsed_body'

    @override
    def _provide_context_data(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if request.content_type != serializer.content_type:
            raise RequestSerializationError(
                'Cannot parse request body '
                f'with content type {request.content_type!r}, '
                f'expected {serializer.content_type!r}',
            )
        try:
            return serializer.from_json(request.body)
        except (msgspec.DecodeError, TypeError) as exc:
            raise RequestSerializationError(str(exc)) from exc


class Headers(ComponentParser, Generic[_HeadersT]):
    """
    Parses request headers.

    # TODO: example

    If your controller class inherits from ``Headers`` - then you can access
    parsed headers as ``self.parsed_headers`` attribute.
    """

    parsed_headers: _HeadersT

    @classmethod
    @override
    def _provide_context_name(cls) -> str:
        return 'parsed_headers'

    @override
    def _provide_context_data(
        self,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return request.headers
