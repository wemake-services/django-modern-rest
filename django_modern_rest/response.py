from http import HTTPMethod, HTTPStatus
from typing import Any, overload

from django.http import HttpResponse

from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import (
    Empty,
    EmptyObj,
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
