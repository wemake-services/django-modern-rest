import dataclasses
from collections.abc import Mapping
from http import HTTPMethod, HTTPStatus
from typing import Any, Generic, TypeVar, overload

from django.http import HttpResponse

from django_modern_rest.headers import (
    HeaderDescription,
    NewHeader,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import (
    Empty,
    EmptyObj,
)

_ItemT = TypeVar('_ItemT')


class APIError(Exception, Generic[_ItemT]):
    """
    Special class to fast return errors from API.

    Does perform the regular response validation.

    Usage:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from django_modern_rest import (
        ...     APIError,
        ...     Controller,
        ...     ResponseDescription,
        ...     modify,
        ... )
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class UserController(Controller[PydanticSerializer]):
        ...     @modify(
        ...         extra_responses=[
        ...             ResponseDescription(
        ...                 str,
        ...                 status_code=HTTPStatus.NOT_FOUND,
        ...             ),
        ...         ],
        ...     )
        ...     def get(self, user_id: int) -> str:
        ...         if user_id < 0:
        ...             raise APIError(
        ...                 'There are no users with ids < 0',
        ...                 status_code=HTTPStatus.NOT_FOUND,
        ...             )
        ...         return f'{user_id}@example.com'  # email

    """

    def __init__(
        self,
        raw_data: _ItemT,
        *,
        status_code: HTTPStatus,
        headers: dict[str, str] | Empty = EmptyObj,
    ) -> None:
        """Create response from parts."""
        super().__init__()
        self.raw_data = raw_data
        self.status_code = status_code
        self.headers = headers


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseDescription:
    """
    Represents a single API response.

    Args:
        return_type: Shows *return_type* in the documentation
            as returned model schema.
            We validate *return_type* to match the returned response content
            by default, but it can be turned off.
        status_code: Shows *status_code* in the documentation.
            We validate *status_code* to match the specified
            one when ``HttpResponse`` is returned.
        headers: Shows *headers* in the documentation.
            When passed, we validate that all given required headers are present
            in the final response. Headers with ``value`` attribute set
            will be added to the final response.

    We use this structure to validate responses and render them in OpenAPI.
    """

    # `type[T]` limits some type annotations, like `Literal[1]`:
    return_type: Any
    status_code: HTTPStatus = dataclasses.field(kw_only=True)
    headers: dict[str, HeaderDescription] | Empty = dataclasses.field(
        kw_only=True,
        default=EmptyObj,
    )

    # TODO: description, examples, etc


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ResponseModification:
    """
    Represents a single API modification.

    Args:
        return_type: Shows *return_type* in the documentation
            as returned model schema.
            We validate *return_type* to match the returned response content
            by default, but it can be turned off.
        status_code: Shows *status_code* in the documentation.
            We validate *status_code* to match the specified
            one when ``HttpResponse`` is returned.
        headers: Shows *headers* in the documentation.
            When passed, we validate that all given required headers are present
            in the final response. Headers with ``value`` attribute set
            will be added to the final response.

    We use this structure to validate responses and render them in OpenAPI.
    """

    # `type[T]` limits some type annotations, like `Literal[1]`:
    return_type: Any
    status_code: HTTPStatus
    headers: Mapping[str, NewHeader] | Empty

    def to_description(self) -> ResponseDescription:
        """Convert response modification to response description."""
        return ResponseDescription(
            return_type=self.return_type,
            status_code=self.status_code,
            headers=(
                EmptyObj
                if isinstance(self.headers, Empty)
                else {
                    header_name: header.to_description()
                    for header_name, header in self.headers.items()
                }
            ),
        )


@overload
def build_response(
    method: HTTPMethod | str,
    serializer: type[BaseSerializer],
    *,
    raw_data: Any,
    headers: dict[str, str] | Empty = EmptyObj,
    status_code: HTTPStatus | Empty = EmptyObj,
) -> HttpResponse: ...


@overload
def build_response(
    method: None,
    serializer: type[BaseSerializer],
    *,
    raw_data: Any,
    status_code: HTTPStatus,
    headers: dict[str, str] | Empty = EmptyObj,
) -> HttpResponse: ...


def build_response(
    method: HTTPMethod | str | None,
    serializer: type[BaseSerializer],
    *,
    raw_data: Any,
    headers: dict[str, str] | Empty = EmptyObj,
    status_code: HTTPStatus | Empty = EmptyObj,
) -> HttpResponse:
    """
    Utility that returns the actual `HttpResponse` object from its parts.

    Does not perform extra validation, only regular response validation.
    We need this as a function, so it can be called when no endpoints exist.

    Do not use directly, prefer using
    :meth:`django_modern_rest.endpoint.Endpoint.to_response` method.

    You have to provide either *method* or *status_code*.
    """
    if not isinstance(status_code, Empty):
        status = status_code
    elif method is not None:
        status = infer_status_code(method)
    else:
        raise ValueError(
            'Cannot pass both `method=None` and `status_code=Empty`',
        )

    response_headers = {} if isinstance(headers, Empty) else headers
    if 'Content-Type' not in response_headers:
        response_headers['Content-Type'] = serializer.content_type

    return HttpResponse(
        content=serializer.to_json(raw_data),
        status=status,
        headers=response_headers,
    )


def infer_status_code(method_name: HTTPMethod | str) -> HTTPStatus:
    """
    Infer status code based on method name.

    >>> from http import HTTPMethod
    >>> infer_status_code(HTTPMethod.POST)
    <HTTPStatus.CREATED: 201>

    >>> infer_status_code('post')
    <HTTPStatus.CREATED: 201>

    >>> infer_status_code('get')
    <HTTPStatus.OK: 200>
    """
    if isinstance(method_name, HTTPMethod):
        method = method_name
    else:
        method = HTTPMethod(method_name.upper())
    if method is HTTPMethod.POST:
        return HTTPStatus.CREATED
    return HTTPStatus.OK
