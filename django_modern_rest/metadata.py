import dataclasses
from http import HTTPMethod, HTTPStatus
from typing import (
    Literal,
    TypeAlias,
    final,
)

from django_modern_rest.response import (
    ResponseDescription,
    ResponseModification,
)
from django_modern_rest.types import (
    Empty,
)

#: Decorator name that was used to create this metadata.
ExplicitDecoratorNameT: TypeAlias = Literal['modify', 'validate'] | None


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadata:
    """
    Base class for common endpoint metadata.

    Attrs:
        responses: Mapping of HTTP method to response description.
            All possible responses that this API can return.
        method: HTTP method for this endpoint.
        validate_responses: Do we have to run runtime validation
            of responses for this endpoint? Customizable via global setting,
            per controller, and per endpoint.
            Here we only store the per endpoint information.
        modification: Default modifications that are applied
            to the returned data. Can be ``None``, when ``@validate`` is used.

    Abstract, cannot be created directly, use specific subclasses for that.
    """

    responses: dict[HTTPStatus, ResponseDescription]
    validate_responses: bool | Empty
    method: HTTPMethod
    modification: ResponseModification | None
