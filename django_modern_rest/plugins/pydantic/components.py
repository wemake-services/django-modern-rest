from typing import Any, ClassVar, Generic, TypeVar

import pydantic
from django.http import HttpRequest
from typing_extensions import override

from django_modern_rest.components import BaseBody, BaseHeaders, BaseQuery
from django_modern_rest.plugins.pydantic.serialization import model_validate

_QueryT = TypeVar('_QueryT', bound=pydantic.BaseModel)
_BodyT = TypeVar('_BodyT', bound=pydantic.BaseModel)
_HeadersT = TypeVar('_HeadersT', bound=pydantic.BaseModel)


class Query(BaseQuery[_QueryT], Generic[_QueryT]):
    """
    Parses query params of the request.

    For example:

    .. code:: python

       >>> import pydantic

       >>> class Ordering(pydantic.BaseModel):
       ...     ordering: str
       ...     reversed: bool

    Will parse a request like ``/api/endpoint/?ordering=price&reversed=true``
    into ``Ordering`` model.

    If your controller class inherits from ``Query`` - then you can access
    parsed query model as ``self.parsed_query`` attribute.
    """

    __is_base_type__: ClassVar[bool] = True

    validate_kwargs: ClassVar[dict[str, Any]] = {}

    @override
    def _parse_component(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.parsed_query = model_validate(
            self.__model__,
            request.GET,
            **self.validate_kwargs,
        )


class Body(BaseBody[_BodyT], Generic[_BodyT]):
    """
    Parses body of the request.

    # TODO: example

    If your controller class inherits from ``Body`` - then you can access
    parsed body as ``self.parsed_body`` attribute.
    """

    __is_base_type__: ClassVar[bool] = True

    validate_kwargs: ClassVar[dict[str, Any]] = {}

    @override
    def _parse_component(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.parsed_body = model_validate(
            self.__model__,
            request.GET,
            **self.validate_kwargs,
        )


class Headers(BaseHeaders[_HeadersT], Generic[_HeadersT]):
    """
    Parses request headers.

    # TODO: example

    If your controller class inherits from ``Headers`` - then you can access
    parsed headers as ``self.parsed_headers`` attribute.
    """

    __is_base_type__: ClassVar[bool] = True

    validate_kwargs: ClassVar[dict[str, Any]] = {}

    @override
    def _parse_component(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.parsed_headers = model_validate(
            self.__model__,
            request.GET,
            **self.validate_kwargs,
        )
