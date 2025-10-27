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
            PydanticSerializer,
            raw_data={
                'detail': 'CSRF verification failed. Request aborted.'
            },
            status_code=HTTPStatus.FORBIDDEN,
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
                PydanticSerializer,
                raw_data={'error': 'Bad request'},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        elif response.status_code == HTTPStatus.UNAUTHORIZED:
            return build_response(
                PydanticSerializer,
                raw_data={'error': 'Unauthorized'},
                status_code=HTTPStatus.UNAUTHORIZED,
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

Understanding the Two-Phase Middleware Pattern
-----------------------------------------------

Django middleware operates in two distinct phases around the view execution.
Understanding this pattern is crucial for effectively using middleware
with ``django-modern-rest``.

The ``get_response`` Callback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every Django middleware receives a ``get_response`` callable parameter.
This is **not** the actual response - it's a callback that represents
the next middleware in the chain or the final view function.

.. code-block:: python

    def my_middleware(
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> Callable[[HttpRequest], HttpResponse]:
        """
        get_response is a callback that will:
        1. Call the next middleware (if any)
        2. Eventually call your controller/view
        3. Return the response
        """

        def middleware_function(request: HttpRequest) -> HttpResponse:
            # Your middleware logic here
            response = get_response(request)  # Call the view
            return response

        return middleware_function

Phase 1: Process Request (Before ``get_response``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before calling ``get_response``, you can:

- Read and validate request data
- Add attributes to the request object
- Perform authentication/authorization
- Short-circuit and return early (without calling the view)

.. code-block:: python

    import uuid
    from collections.abc import Callable
    from django.http import HttpRequest, HttpResponse

    def add_request_id_middleware(
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> Callable[[HttpRequest], HttpResponse]:
        """Adds a unique request_id to every request."""

        def decorator(request: HttpRequest) -> HttpResponse:
            request_id = str(uuid.uuid4())
            request.request_id = request_id  # Add attribute to request

            response = get_response(request)
            response['X-Request-ID'] = request_id

            return response

        return decorator

Now your controller can access ``self.request.request_id``:

.. code-block:: python

    @add_request_id_json
    class MyController(Controller[PydanticSerializer]):
        def get(self) -> dict[str, str]:
            # Access the request_id added by middleware
            request_id = self.request.request_id
            return {'request_id': request_id}

Phase 2: Process Response (After ``get_response``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After calling ``get_response``, you can:

- Modify the response object
- Add headers
- Log response details
- Transform response content

.. code-block:: python

    def custom_header_middleware(
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> Callable[[HttpRequest], HttpResponse]:
        """Adds custom headers to all responses."""

        def decorator(request: HttpRequest) -> HttpResponse:
            # Call the view first
            response = get_response(request)

            response['X-Custom-Header'] = 'CustomValue'
            response['X-Processed-By'] = 'custom_header_middleware'

            return response

        return decorator

Short-Circuiting: Returning Without Calling ``get_response``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Middleware can return a response **without** calling ``get_response``.
This is called "short-circuiting" - the view is never executed.

Common use cases:

- Authentication failures (return 401)
- Rate limiting (return 429)
- Request validation failures (return 400)
- Cache hits (return cached response)

.. code-block:: python

    from http import HTTPStatus
    from django_modern_rest import build_response
    from django_modern_rest.plugins.pydantic import PydanticSerializer

    def require_auth_middleware(
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> Callable[[HttpRequest], HttpResponse]:
        """Requires authentication - returns 401 if missing."""

        def decorator(request: HttpRequest) -> HttpResponse:
            # Check authentication BEFORE calling view
            token = request.headers.get('X-Auth-Token')

            if not token or not token.startswith('user_'):
                # Return 401 WITHOUT calling get_response
                # The view is never executed
                return build_response(
                    PydanticSerializer,
                    raw_data={'detail': 'Authentication required'},
                    status_code=HTTPStatus.UNAUTHORIZED,
                )

            # Parse token and add user info to request
            try:
                user_id = int(token.replace('user_', ''))
                request.user_id = user_id
                request.authenticated = True
            except ValueError:
                return build_response(
                    PydanticSerializer,
                    raw_data={'detail': 'Invalid authentication token'},
                    status_code=HTTPStatus.UNAUTHORIZED,
                )

            # Authentication successful - call the view
            response = get_response(request)
            response['X-Authenticated'] = 'true'

            return response

        return decorator

Use with ``wrap_middleware``:

.. code-block:: python

    @wrap_middleware(
        require_auth_middleware,
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )
    def require_auth_json(response: HttpResponse) -> HttpResponse:
        """Converter for 401 responses."""
        return response

    @require_auth_json
    class ProtectedController(Controller[PydanticSerializer]):
        responses = [*require_auth_json.responses]

        def get(self) -> dict[str, int]:
            # This only executes if authentication succeeds
            user_id = self.request.user_id
            return {'user_id': user_id}

Complete Example: Authentication Middleware
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a complete example combining both phases:

.. code-block:: python

    def auth_middleware(
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> Callable[[HttpRequest], HttpResponse]:
        """Adds authentication info to request (like Django's AuthenticationMiddleware)."""

        def decorator(request: HttpRequest) -> HttpResponse:
            token = request.headers.get('X-Auth-Token')

            if token and token.startswith('user_'):
                try:
                    user_id = int(token.replace('user_', ''))
                    request.user_id = user_id
                    request.authenticated = True
                except ValueError:
                    request.authenticated = False
            else:
                request.authenticated = False

            response = get_response(request)

            if request.authenticated:
                response['X-Authenticated'] = 'true'

            return response

        return decorator

Visual Flow
~~~~~~~~~~~

Here's how a request flows through middleware:

.. code-block:: text

    HTTP Request
        ↓
    Middleware 1 (Phase 1: process request)
        ↓
    Middleware 2 (Phase 1: process request)
        ↓
    Controller/View executes
        ↓
    Middleware 2 (Phase 2: process response)
        ↓
    Middleware 1 (Phase 2: process response)
        ↓
    HTTP Response


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
            PydanticSerializer,
            raw_data={'detail': 'CSRF verification failed. Request aborted.'},
            status_code=HTTPStatus.FORBIDDEN,
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
