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

    def middleware_function(request: HttpRequest) -> HttpResponse:  # noqa: WPS430
        # Your middleware logic here
        response = get_response(request)  # Call the view
        return response  # noqa: RET504

    return middleware_function
