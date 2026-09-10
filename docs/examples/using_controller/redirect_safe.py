from typing import Never

from django.http import HttpRequest
from django.utils.http import url_has_allowed_host_and_scheme

from dmr import RedirectTo


def redirect_to_next(request: HttpRequest, next_url: str) -> Never:
    url_is_safe = url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    raise RedirectTo(next_url if url_is_safe else '/')
