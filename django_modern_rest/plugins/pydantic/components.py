from typing import Any, ClassVar, Generic, TypeVar

import pydantic
from django.http import HttpRequest
from typing_extensions import override

from django_modern_rest.components import BaseQuery
from django_modern_rest.plugins.pydantic.serialization import model_validate

_QueryT = TypeVar('_QueryT', bound=pydantic.BaseModel)


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
