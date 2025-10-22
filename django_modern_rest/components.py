import abc
from typing import Any, ClassVar, Generic, TypeVar

from django.http import HttpRequest
from typing_extensions import override

from django_modern_rest.exceptions import (
    DataParsingError,
    RequestSerializationError,
)
from django_modern_rest.response import ResponseDescription
from django_modern_rest.serialization import BaseSerializer

_QueryT = TypeVar('_QueryT')
_BodyT = TypeVar('_BodyT')
_HeadersT = TypeVar('_HeadersT')
_PathT = TypeVar('_PathT')


class ComponentParser:
    """Base abstract provider for request components."""

    # Public API:
    context_name: ClassVar[str]

    # Internal API:
    __is_base_type__: ClassVar[bool] = True

    @abc.abstractmethod
    def provide_context_data(
        self,
        serializer: type[BaseSerializer],
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Return unstructured raw value for serializer.from_python().

        Implement body JSON decoding / content-type checks here if needed.
        """
        raise NotImplementedError

    @classmethod
    def provide_responses(
        cls,
        serializer: type[BaseSerializer],
        model: Any,
    ) -> list[ResponseDescription]:
        """
        Return a list of extra responses that this component produces.

        For example, when parsing something, we always have an option
        to fail a parsing, if some request does not fit our model.
        """
        return [
            ResponseDescription(
                # We do this for runtime validation, not static type check:
                serializer.response_parsing_error_model,
                status_code=RequestSerializationError.status_code,
            ),
        ]


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
    context_name: ClassVar[str] = 'parsed_query'

    @override
    def provide_context_data(
        self,
        serializer: type[BaseSerializer],
        model: Any,
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
    context_name: ClassVar[str] = 'parsed_body'

    @override
    def provide_context_data(
        self,
        serializer: type[BaseSerializer],
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if request.content_type != serializer.content_type:
            raise RequestSerializationError(
                serializer.error_serialize(
                    'Cannot parse request body '
                    f'with content type {request.content_type!r}, '
                    f'expected {serializer.content_type!r}',
                ),
            )
        try:
            return serializer.deserialize(request.body)
        except DataParsingError as exc:
            raise RequestSerializationError(
                serializer.error_serialize(str(exc)),
            ) from exc


class Headers(ComponentParser, Generic[_HeadersT]):
    """
    Parses request headers.

    # TODO: example

    If your controller class inherits from ``Headers`` - then you can access
    parsed headers as ``self.parsed_headers`` attribute.
    """

    parsed_headers: _HeadersT
    context_name: ClassVar[str] = 'parsed_headers'

    @override
    def provide_context_data(
        self,
        serializer: type[BaseSerializer],
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return request.headers


class Path(ComponentParser, Generic[_PathT]):
    """
    Parses the url part of the request.

    # TODO: example

    If your controller class inherits from ``Path`` - then you can access
    parsed paths parameters as ``self.parsed_path`` attribute.

    It is way stricter than the original Django's routing system.
    For example, django allows to
    """

    parsed_path: _PathT
    context_name: ClassVar[str] = 'parsed_path'

    @override
    def provide_context_data(
        self,
        serializer: type[BaseSerializer],
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return kwargs
