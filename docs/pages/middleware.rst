Middleware
==========

As by our main principle, you can use any default
Django middleware with your API. But, it has several minor problems by default:

1. Any middleware responses won't show up in your schema
2. Responses won't have the right ``'Content-Type'``
3. Responses won't be validated

That's why ``django-modern-rest`` provides a powerful middleware
system that allows you to wrap Django middleware around your controllers
while maintaining proper OpenAPI documentation and response handling.

The main function for this
is :func:`~django_modern_rest.decorators.wrap_middleware`,
which creates reusable decorators that can be applied to controller classes.

How it works
------------

``wrap_middleware`` is a factory function that creates decorators
with pre-configured middleware. It takes:

1. A middleware function or class
2. One or more :class:`~django_modern_rest.response.ResponseDescription` objects
3. Returns a decorator factory that takes a response converter function

The created decorator:
- Wraps the controller's dispatch method with the specified middleware
- Handles both sync and async controllers automatically
- Applies response conversion when the middleware returns a specific status code
- Adds the response descriptions to the controller's OpenAPI schema

Basic Usage
-----------

Let's create a simple middleware decorator for CSRF protection:

.. code-block:: python

    from django.views.decorators.csrf import csrf_protect
    from django.http import HttpResponse
    from http import HTTPStatus
    from django_modern_rest import (
        Controller,
        ResponseDescription,
        wrap_middleware,
    )
    from django_modern_rest.plugins.pydantic import PydanticSerializer

    @wrap_middleware(
        csrf_protect,
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.FORBIDDEN,
        ),
    )
    def csrf_protect_json(response: HttpResponse) -> HttpResponse:
        return build_response(
            None,
            PydanticSerializer,
            raw_data={
                'detail': 'CSRF verification failed. Request aborted.'
            },
            status_code=HTTPStatus(response.status_code),
        )

    @csrf_protect_json
    class MyController(Controller[PydanticSerializer]):
        responses = [
            *csrf_protect_json.responses,
        ]

        def post(self) -> dict[str, str]:
            return {'message': 'ok'}

In this example:

1. We create a middleware decorator using ``wrap_middleware``
2. The decorator wraps ``csrf_protect`` middleware around the controller
3. When CSRF verification fails, our converter function
   transforms the response to JSON
4. The response description is automatically added to the OpenAPI schema

Custom Middleware
-----------------

You can also create custom middleware functions.
Here's an example of a rate limiting middleware:

.. code-block:: python

    from collections.abc import Callable
    from http import HTTPStatus
    from django.http import HttpRequest, HttpResponse
    from django_modern_rest import build_response, wrap_middleware
    from django_modern_rest.plugins.pydantic import PydanticSerializer

    def rate_limit_middleware(
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> Callable[[HttpRequest], HttpResponse]:
        """Middleware that simulates rate limiting."""

        def decorator(request: HttpRequest) -> HttpResponse:
            if request.headers.get('X-Rate-Limited') == 'true':
                return build_response(
                    None,
                    PydanticSerializer,
                    raw_data={'detail': 'Rate limit exceeded'},
                    status_code=HTTPStatus.TOO_MANY_REQUESTS,
                )
            return get_response(request)

        return decorator

    @wrap_middleware(
        rate_limit_middleware,
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
        ),
    )
    def rate_limit_json(response: HttpResponse) -> HttpResponse:
        """Pass through the rate limit response."""
        return response

    @rate_limit_json
    class RateLimitedController(Controller[PydanticSerializer]):
        responses = [
            *rate_limit_json.responses,
        ]

        def post(self) -> dict[str, str]:
            return {'message': 'Request processed'}

Multiple Response Descriptions
------------------------------

You can specify multiple response descriptions for different status codes:

.. code-block:: python

    from http import HTTPStatus

    from django_modern_rest.response import build_response

    @wrap_middleware(
        custom_middleware,
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.BAD_REQUEST,
        ),
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )
    def multi_status_middleware(response: HttpResponse) -> HttpResponse:
        """Handle multiple status codes."""
        if response.status_code == HTTPStatus.BAD_REQUEST:
            return build_response(
                {'error': 'Bad request'},
                status_code=response.status_code,
            )
        elif response.status_code == HTTPStatus.UNAUTHORIZED:
            return build_response(
                {'error': 'Unauthorized'},
                status_code=response.status_code,
            )
        return response

Async Controllers
-----------------

``wrap_middleware`` works seamlessly with both sync and async controllers:

.. code-block:: python

    @csrf_protect_json
    class AsyncController(Controller[PydanticSerializer]):
        responses = [
            *csrf_protect_json.responses,
        ]

        async def post(self) -> dict[str, str]:
            # Your async logic here
            return {'message': 'async response'}

The middleware will automatically detect whether the controller is async
and handle it appropriately.

Response Converter Function
---------------------------

The response converter function is called when the middleware returns
a response with a status code that matches one
of the provided response descriptions. This allows you to:

- Transform error responses to JSON format
- Add custom headers
- Modify response content
- Apply consistent error formatting across your API

The converter function receives the original response and should
return a modified :class:`django.http.HttpResponse`.

Best Practices
--------------

1. **Always include response descriptions**: This ensures your OpenAPI
   documentation is complete and accurate.

2. **Use consistent error formatting**: Create reusable converter functions
   that format errors consistently across your API.

3. **Handle both sync and async**: The same middleware decorator works
   with both sync and async controllers.

4. **Test your middleware**: Make sure to test both the success
   and error cases for your middleware.

5. **Document your middleware**: Add docstrings to explain what
   your middleware does and when it's triggered.

Example: Complete CSRF Protection Setup
----------------------------------------

Here's a complete example showing how to set up CSRF protection for a REST API:

.. code-block:: python

    from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
    from django.http import HttpResponse, JsonResponse
    from http import HTTPStatus
    from django_modern_rest import (
        Controller,
        ResponseDescription,
        wrap_middleware,
    )
    from django_modern_rest.response import build_response
    from django_modern_rest.plugins.pydantic import PydanticSerializer

    # CSRF protection for POST/PUT/DELETE requests
    @wrap_middleware(
        csrf_protect,
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.FORBIDDEN,
        ),
    )
    def csrf_protect_json(response: HttpResponse) -> HttpResponse:
        return build_response(
            {'detail': 'CSRF verification failed. Request aborted.'},
            status=HTTPStatus.FORBIDDEN,
        )

    # CSRF cookie for GET requests
    @wrap_middleware(
        ensure_csrf_cookie,
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.OK,
        ),
    )
    def ensure_csrf_cookie_json(response: HttpResponse) -> HttpResponse:
        return response

    @csrf_protect_json
    class ProtectedController(Controller[PydanticSerializer]):
        responses = [
            *csrf_protect_json.responses,
        ]

        def get(self) -> dict[str, str]:
            """Get CSRF token."""
            return {'message': 'Use this endpoint to get CSRF token'}

        def post(self) -> dict[str, str]:
            """Protected endpoint requiring CSRF token."""
            return {'message': 'Successfully created resource'}

    @ensure_csrf_cookie_json
    class PublicController(Controller[PydanticSerializer]):
        responses = [
            *ensure_csrf_cookie_json.responses,
        ]

        def get(self) -> dict[str, str]:
            """Public endpoint that sets CSRF cookie."""
            return {'message': 'CSRF cookie set'}
