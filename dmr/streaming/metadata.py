import dataclasses
from collections.abc import Mapping
from http import HTTPStatus
from types import MappingProxyType
from typing import Any, Final, final

from dmr.cookies import CookieSpec
from dmr.headers import HeaderSpec, NewHeader
from dmr.metadata import ResponseModification, ResponseSpec
from dmr.openapi.objects import Link, Reference

STREAMING_HEADERS_SPEC: Final = MappingProxyType({
    'Cache-Control': HeaderSpec(),
    'X-Accel-Buffering': HeaderSpec(),
    # WSGI cannot provide `Connection` header in `DEBUG` mode:
    'Connection': HeaderSpec(skip_validation=True),
})


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class StreamResponseModification(ResponseModification):
    """
    Provide extra metadata for streaming responses.

    Since we set several headers in ``StreamingResponse``,
    we need to add default header values.
    """

    headers: Mapping[str, 'NewHeader | HeaderSpec'] | None

    def __post_init__(self) -> None:
        """Set header specs if it is missing."""
        if self.headers is None:
            object.__setattr__(self, 'headers', STREAMING_HEADERS_SPEC)


def streaming_response_spec(  # noqa: WPS211
    return_type: Any,
    *,
    content_type: str | set[str],
    status_code: HTTPStatus = HTTPStatus.OK,
    headers: Mapping[str, 'HeaderSpec'] | None = None,
    cookies: Mapping[str, 'CookieSpec'] | None = None,
    links: dict[str, 'Link | Reference'] | None = None,
    description: str | None = None,
) -> ResponseSpec:
    """
    Helper function to create a ``ResponseSpec`` instance for streaming.

    Reduces the boilerplate, but does nothing special.
    """
    headers = {
        **STREAMING_HEADERS_SPEC,
        **(headers or {}),
    }
    return ResponseSpec(
        return_type,
        status_code=status_code,
        headers=headers,
        cookies=cookies,
        streaming=True,
        limit_to_content_types=(
            content_type if isinstance(content_type, set) else {content_type}
        ),
        links=links,
        description=description,
    )
