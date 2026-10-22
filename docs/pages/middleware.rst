Middleware
==========

As per our main principle, you can use any default
Django middleware with your API. But, it has several minor problems by default:

1. Any middleware responses won't show up in your schema
2. Responses won't have the right ``'Content-Type'``
3. Responses won't be validated

That's why ``django-modern-rest`` provides a powerful middleware
system that allows you to wrap Django middleware around your controllers
while maintaining proper OpenAPI documentation and response handling.

The main function for this
is :func:`~dmr.decorators.wrap_middleware`,
which creates reusable decorators that can be applied to controller classes.

How it works
------------

``wrap_middleware`` is a factory function that creates decorators
with pre-configured middleware. It takes:

1. A middleware function or class
2. One or more :class:`~dmr.metadata.ResponseSpec` objects
3. Returns a decorator factory that takes a response converter function

The created decorator:
- Wraps the controller's dispatch method with the specified middleware
- Handles both sync and async controllers automatically
- Applies response conversion when the middleware returns a specific status code
- Adds the response descriptions to the controller's OpenAPI schema

Basic Usage
-----------

Let's add conditional requests to a controller
with Django's :func:`~django.views.decorators.http.condition` decorator:

.. literalinclude:: /examples/middleware/condition_etag.py
    :linenos:
    :language: python


In this example:

1. We create a middleware decorator using ``wrap_middleware``
2. The decorator wraps ``condition`` around the controller,
   which answers ``304 Not Modified`` when the client
   sends the current ``ETag`` in ``If-None-Match``
3. Our converter function adds the ``Content-Type``
   that Django's ``304`` response does not have
4. The ``304`` response description is automatically added
   to the OpenAPI schema

See :ref:`conditional-requests` for more about ``ETag`` support.

.. _custom-middleware:

Custom Middleware
-----------------

You can also create custom middleware functions.
Here's an example of a rate limiting middleware:

.. literalinclude:: /examples/middleware/rate_limit.py
    :linenos:
    :language: python

Multiple Response Descriptions
------------------------------

You can specify multiple response descriptions for different status codes:

.. literalinclude:: /examples/middleware/multi_status.py
  :linenos:
  :language: python

Async Controllers
-----------------

``wrap_middleware`` works seamlessly with both sync and async controllers.
Here's a maintenance mode middleware on an async controller:

.. literalinclude:: /examples/middleware/async_controller.py
  :linenos:
  :language: python

The middleware will automatically detect whether the controller is async
and handle it appropriately.

For async controllers ``get_response`` returns a coroutine.
A middleware can return it as is, like the one above.
To change the response, define the inner function with ``async def``
and ``await get_response(request)`` first.

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

get_response callback
~~~~~~~~~~~~~~~~~~~~~

Every Django middleware receives a ``get_response`` callable parameter.
This is **not** the actual response - it's a callback that represents
the next middleware in the chain or the final view function.

.. literalinclude:: /examples/middleware/get_response.py
  :linenos:
  :language: python

Phase 1: Process Request (before get_response)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before calling ``get_response``, you can:

- Read and validate request data
- Add attributes to the request object
- Perform authentication/authorization
- Short-circuit and return early (without calling the view)

.. literalinclude:: /examples/middleware/add_request_id.py
  :linenos:
  :language: python

Wrap your middleware:

.. literalinclude:: /examples/middleware/wrap_add_request_id.py
  :linenos:
  :language: python

Now your controller can access ``self.request.request_id``:

.. literalinclude:: /examples/middleware/usage_add_request_id.py
  :linenos:
  :language: python

Phase 2: Process Response (after get_response)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After calling ``get_response``, you can:

- Modify the response object
- Add headers
- Log response details
- Transform response content

.. literalinclude:: /examples/middleware/custom_header.py
  :linenos:
  :language: python

Short-Circuiting: Returning Without Calling get_response
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Middleware can return a response **without** calling ``get_response``.
This is called "short-circuiting" - the view is never executed.

Common use cases:

- Rate limiting (return 429)
- Request validation failures (return 400)
- Cache hits (return cached response)
- Custom authentication/authorization checks

See the rate limiting middleware in :ref:`custom-middleware`
for an example.

Wrapping Django's Built-in Decorators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can wrap Django's built-in authentication decorators like ``login_required``
to make them REST API friendly. By default, ``login_required`` returns a 302
redirect, but you can convert it to a JSON 401 response:

.. literalinclude:: /examples/middleware/built_in_decorators.py
  :linenos:
  :language: python

Visual Flow
~~~~~~~~~~~

Here's how a request flows through middleware:

.. mermaid::
  :caption: Middleware execution flow
  :config: {"theme": "forest"}

    graph TB
      A[HTTP Request] --> B1[Middleware 1<br/>Phase 1: process request]
      B1 --> B2[Middleware 2<br/>Phase 1: process request]
      B2 --> C[Controller/View executes]
      C --> D2[Middleware 2<br/>Phase 2: process response]
      D2 --> D1[Middleware 1<br/>Phase 2: process response]
      D1 --> E[HTTP Response]

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

CSRF protection
---------------

Do not wrap :func:`~django.views.decorators.csrf.csrf_protect`
around your controllers, set ``csrf_exempt = False`` instead.
Then ``django-modern-rest`` documents the ``403`` response
and the ``csrf`` security scheme for unsafe methods only,
and :func:`~dmr.security.csrf.build_csrf_handler`
returns CSRF failures in the error format of your API.
See :ref:`controller-csrf`.

Clients send the ``csrftoken`` cookie and the same value
in the ``X-CSRFToken`` header. Django sets the cookie on login
and whenever ``django.middleware.csrf.get_token`` is called.
