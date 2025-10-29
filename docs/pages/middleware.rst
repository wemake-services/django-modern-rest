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

.. literalinclude:: /examples/middleware/csrf_protect_json.py
    :caption: csrf_protect_json.py
    :language: python
    :linenos:

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

.. literalinclude:: /examples/middleware/rate_limit.py
    :caption: rate_limit.py
    :language: python
    :linenos:

Multiple Response Descriptions
------------------------------

You can specify multiple response descriptions for different status codes:

.. literalinclude:: /examples/middleware/multi_status.py
  :caption: multi_status.py
  :language: python
  :linenos:

Async Controllers
-----------------

``wrap_middleware`` works seamlessly with both sync and async controllers:

.. literalinclude:: /examples/middleware/async_controller.py
  :caption: async_controller.py
  :language: python
  :linenos:

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

.. literalinclude:: /examples/middleware/complete_csrf_setup.py
  :caption: complete_csrf_setup.py
  :language: python
  :linenos:
