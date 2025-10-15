import abc
from typing import Any, ClassVar, Generic, TypeVar

from django.http import HttpRequest
from typing_extensions import override

from django_modern_rest.serialization import BaseSerializer

_QueryT = TypeVar('_QueryT')
_BodyT = TypeVar('_BodyT')
_HeadersT = TypeVar('_HeadersT')


class ComponentParserMixin:
    """Base abtract parser for request components."""

    # Public API:
    strict_validation: ClassVar[bool] = False

    # Internal API:
    __is_base_type__: ClassVar[bool] = True

    @classmethod
    @abc.abstractmethod
    def _provide_context_name(cls) -> str:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _provide_context_data(
        cls,
        request: HttpRequest,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
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
    def _provide_context_name(cls) -> str:
        return 'parsed_query'

    @classmethod
    @override
    def _provide_context_data(
        cls,
        request: HttpRequest,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return request.GET


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
    def _provide_context_name(cls) -> str:
        return 'parsed_body'

    @classmethod
    @override
    def _provide_context_data(
        cls,
        request: HttpRequest,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return serializer.from_json(request.body)


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
    def _provide_context_name(cls) -> str:
        return 'parsed_headers'

    @classmethod
    @override
    def _provide_context_data(
        cls,
        request: HttpRequest,
        serializer: type[BaseSerializer],
        type_args: tuple[Any, ...],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return request.headers
