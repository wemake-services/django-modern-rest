from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from dmr.cookies import CookieSpec
from dmr.headers import HeaderSpec
from dmr.metadata import ResponseSpec
from dmr.openapi.objects import Link, Reference


def streaming_response_spec(
    return_type: Any,
    *,
    content_type: str,
    status_code: HTTPStatus = HTTPStatus.OK,
    headers: Mapping[str, 'HeaderSpec'] | None = None,
    cookies: Mapping[str, 'CookieSpec'] | None = None,
    links: dict[str, 'Link | Reference'] | None = None,
    description: str | None = None,
) -> ResponseSpec:
    headers = {
        'Cache-Control': HeaderSpec(),
        'X-Accel-Buffering': HeaderSpec(),
        # WSGI cannot provide `Connection` header in `DEBUG` mode:
        'Connection': HeaderSpec(skip_validation=True),
        **(headers or {}),
    }
    return ResponseSpec(
        return_type,
        status_code=status_code,
        headers=headers,
        cookies=cookies,
        streaming=True,
        limit_to_content_types={content_type},
        links=links,
        description=description,
    )
