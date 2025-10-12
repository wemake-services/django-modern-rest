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

    __is_base_type__: ClassVar[bool] = True

    # TODO: use a TypedDict
    from_python_kwargs: ClassVar[dict[str, Any]] = {}

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
        self.parsed_query = serializer.from_python(
            request.GET,
            type_args[0],
            self.from_python_kwargs,
        )


class Body(ComponentParserMixin, Generic[_BodyT]):
    """
    Parses body of the request.

    # TODO: example

    If your controller class inherits from ``Body`` - then you can access
    parsed body as ``self.parsed_body`` attribute.
    """

    parsed_body: _BodyT

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
        unstructured = serializer.from_json(request.body)
        self.parsed_body = serializer.from_python(
            unstructured,
            type_args[0],
            self.from_python_kwargs,
        )


class Headers(ComponentParserMixin, Generic[_HeadersT]):
    """
    Parses request headers.

    # TODO: example

    If your controller class inherits from ``Headers`` - then you can access
    parsed headers as ``self.parsed_headers`` attribute.
    """

    parsed_headers: _HeadersT

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
        self.parsed_headers = serializer.from_python(
            request.headers,
            type_args[0],
            self.from_python_kwargs,
        )
