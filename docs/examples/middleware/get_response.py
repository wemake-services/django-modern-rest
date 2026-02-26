from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


def my_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    """
    get_response is a callback.

    It will:
    1. Call the next middleware (if any)
    2. Eventually call your controller/view
    3. Return the response
    """

    def factory(request: HttpRequest) -> HttpResponse:
        # Your middleware logic here:
        return get_response(request)  # Call the view

    return factory
