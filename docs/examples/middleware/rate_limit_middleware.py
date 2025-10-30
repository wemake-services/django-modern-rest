from collections.abc import Callable
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse

from django_modern_rest import build_response
from django_modern_rest.plugins.pydantic import PydanticSerializer


def rate_limit_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    """Middleware that blocks rate-limited requests."""

    def decorator(request: HttpRequest) -> HttpResponse:
        # Check rate limit BEFORE calling view
        if request.headers.get('X-Rate-Limited') == 'true':
            # Return 429 WITHOUT calling get_response
            # The view is never executed
            return build_response(
                PydanticSerializer,
                raw_data={'detail': 'Rate limit exceeded'},
                status_code=HTTPStatus.TOO_MANY_REQUESTS,
            )

        # Rate limit OK - call the view
        return get_response(request)

    return decorator
