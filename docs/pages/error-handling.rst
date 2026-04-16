Error handling
==============

``django-modern-rest`` has 3 layers where errors might be handled.
It provides flexible error handling logic
on :class:`~dmr.endpoint.Endpoint`,
:class:`~dmr.controller.Controller`,
and :func:`global <dmr.errors.global_error_handler>` levels.

All error handling functions always accept 3 arguments:

1. :class:`~dmr.endpoint.Endpoint` where error happened
2. :class:`~dmr.controller.Controller` where error happened
3. Exception that happened

Here's how it works:

1. We first try to call ``error_handler`` that was passed into the endpoint
   definition via :func:`~dmr.endpoint.modify`
   or :func:`~dmr.endpoint.validate`
2. If it returns :class:`django.http.HttpResponse`, return it to the user
3. If it raises, call
   :meth:`~dmr.controller.Controller.handle_error` for sync
   controllers
   and :meth:`~dmr.controller.Controller.handle_async_error`
   for async controllers
4. If controller's handler returns :class:`~django.http.HttpResponse`,
   return it to the user
5. If it raises, call configured global error handler, by default
   it is :func:`~dmr.errors.global_error_handler`
   (it is always sync)

.. warning::

  There are two things to keep in mind:

  1. Async endpoints will require async ``error_handler`` parameter,
     Sync endpoints will require sync ``error_handler`` parameter.
     This is validated on endpoint creation
  2. We don't allow to define sync ``handle_error`` handlers
     for async controllers.
     We also don't allow async ``handle_async_error`` handlers
     for sync controllers.

.. note::

  :exc:`~dmr.response.APIError` does not follow any of these
  rules and has a default handler, which will convert an instance
  of ``APIError`` to :class:`~django.http.HttpResponse` via
  :meth:`~dmr.controller.Controller.to_error` call.

  You don't need to catch ``APIError`` in any way,
  unless you know what you are doing.


Customizing endpoint error handler
----------------------------------

Let's pass custom error handling to a single endpoint:

.. literalinclude:: /examples/error_handling/endpoint.py
  :caption: views.py
  :language: python
  :linenos:

In this example we add error handling defined as ``division_error``
to ``patch`` endpoint (which serves as a division operation),
while keeping ``post`` endpoint (which serves as a multiply operation)
without a custom error handler.
Because :exc:`ZeroDivisionError` can't happen in ``post``.

Per-endpoint's error handling has a priority
over per-controller and global handlers.

You can also define endpoint error handlers as controller methods
and pass them wrapped with :func:`~dmr.errors.wrap_handler`
as handlers. Like so:

.. literalinclude:: /examples/error_handling/wrap_endpoint.py
  :caption: views.py
  :language: python
  :linenos:

Customizing controller error handler
------------------------------------

Let's create custom error handling for the whole controller:

.. literalinclude:: /examples/error_handling/controller.py
  :caption: views.py
  :language: python
  :linenos:

In this example we are using `zapros <https://github.com/kap-sh/zapros>`_
HTTP client to proxy an HTTP ``GET`` and ``POST``
requests to some other API service.
If we fail to send a request and raise a specific HTTP client error,
we return an error with ``424`` error code.


Going further
-------------

Now you can understand how you can create:

- Endpoints with custom error handlers
- Controllers with custom error handlers
- :class:`~dmr.metadata.ResponseSpec` objects
  for new error response schemas

You can dive even deeper and:

- Subclass :attr:`~dmr.controller.Controller`
  and provide default error handling for this specific subclass
- Redefine :attr:`~dmr.controller.Controller.endpoint_cls`
  and change how one specific endpoint behaves on a deep level,
  see :meth:`~dmr.endpoint.Endpoint.handle_error`
  and :meth:`~dmr.endpoint.Endpoint.handle_async_error`


Error handling diagram
----------------------

The same error handling logic can be represented as a diagram:

.. mermaid::
  :caption: Error handling logic
  :config: {"theme": "forest"}

  graph TB
      Start[Request] --> Error{Error?};
      Error -->|Yes| Endpoint[Endpoint-level handler];
      Endpoint --> EndpointHandler{Raises or returns response?};
      EndpointHandler -->|response| Failure[Error response];
      EndpointHandler -->|raises| Controller[Controller-level handler];
      Controller --> ControllerHandler{Raises or returns response?};
      ControllerHandler -->|response| Failure[Error response];
      ControllerHandler -->|raises| Global[Global handler];
      Global --> GlobalHandler{Raises or returns response?};
      GlobalHandler -->|response| Failure[Error response];
      GlobalHandler -->|raises| Reraises[Reraises error];
      Error ---->|No| Success[Successful response];

.. note::

  If :ref:`handler500` is configured, it will catch all unhandled errors
  in the provided scope and return ``500`` errors with the correct payload.


.. _customizing-error-messages:

Customizing error messages
--------------------------

All error messages, including pre-defined ones, can be easily customized
on a per-controller basis.

To do so, you would need to change:

1. :attr:`~dmr.controller.Controller.error_model` attribute for
   all controllers that will be using this error message schema
2. :meth:`~dmr.controller.Controller.format_error` method
   to provide custom runtime error formatting

.. literalinclude:: /examples/error_handling/custom_error_messages.py
  :caption: views.py
  :language: python
  :linenos:

This will also change the OpenAPI schema for the affected controller.

See :class:`~dmr.errors.ErrorModel`
for the default error model schema.
And :func:`~dmr.errors.format_error`
for the default error formatting.

See :ref:`content negotiation <error-model-negotiation>`
docs about how to use different error models
for different content types.

Customizing error headers and cookies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say you want to customize how all errors responses behave
and add a header, for example, ``X-Error-Id`` from your error tracking system.

How this can be done?

.. literalinclude:: /examples/error_handling/custom_error_headers.py
  :caption: views.py
  :language: python
  :linenos:

To attach response headers or cookies to the error model
we use :class:`~dmr.metadata.ResponseSpecMetadata`
inside :data:`typing.Annotated` type.

We also have to redefine :meth:`~dmr.controller.Controller.to_error`
to add missing ``X-Error-Id`` headers for your error responses.

You can do the same for all responses, not just failing ones.
For this, override :meth:`~dmr.controller.Controller.to_response`.

This can also be used to attach ``RateLimit`` headers
and other :doc:`throttling` information.


Problem Details
---------------

.. seealso::

  RFC: https://datatracker.ietf.org/doc/html/rfc9457

``django-modern-rest`` supports customizing of all error message
inside the framework, including builtin ones.

:class:`~dmr.problem_details.ProblemDetailsError`
is a great example of how it can be done.

It is a regular subclass of :class:`~dmr.response.APIError`,
which does not have any special handling inside our framework.
This is done on purpose, so we can be sure that users also can
to customize their exceptions any way they need.

We support two main use-cases for Problem Details.

Always raising Problem Details
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To always use :class:`~dmr.problem_details.ProblemDetailsError`
inside your controller you would need to:

1. Define :attr:`~dmr.controller.Controller.error_model` attribute
   as :class:`~dmr.problem_details.ProblemDetailsModel`
2. Raise an exception itself, pass all the required fields
3. Convert other message to the Problem Details format
   using :meth:`~dmr.controller.Controller.format_error` method

.. literalinclude:: /examples/error_handling/problem_details.py
  :caption: views.py
  :language: python
  :linenos:

Conditionally raising Problem Details
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Another way is to :doc:`negotiate <negotiation>` the error response format.
How does it work?

1. When user sends a request with ``Accept`` header
   with ``application/problem+json`` content type,
   we will return Problem Details errors
2. When ``application/json`` or any other content type is sent,
   we return regular :class:`~dmr.errors.ErrorModel` error payloads

To do so, you would need a slightly more difficult setup:

1. Define :attr:`~dmr.controller.Controller.error_model` attribute
   as the result of :meth:`~dmr.problem_details.ProblemDetailsError.error_model`
   method call. It will add :ref:`conditional schema types <conditional-types>`
   to your error responses
2. Define several :class:`~dmr.renderers.Renderer` types,
   including the one which will handle ``application/problem+json``
3. Raise a conditional exception:
   use :meth:`~dmr.problem_details.ProblemDetailsError.conditional_error`
   to only raise Problem Details when the correct accepted type is passed
4. Convert other message to the Problem Details format
   using :meth:`~dmr.controller.Controller.format_error`
   method when the correct accepted type is passed

.. literalinclude:: /examples/error_handling/problem_details_negotiation.py
  :caption: views.py
  :language: python
  :linenos:

.. tip::

  You can still make ``application/problem+json`` the default
  and when ``application/json`` (or any other type) is explicitly requested
  return the :class:`~dmr.errors.ErrorModel` errors.


Handling validation errors from models
--------------------------------------

When creating models with, for example, :class:`pydantic.BaseModel`,
your validation can fail. This error will not be handled by design.

Why? Because catching all specific validation errors for a specific serializer
that can happen in your application will do more harm than good.

This is the default behavior:

.. literalinclude:: /examples/error_handling/pydantic_validation_error.py
  :caption: views.py
  :language: python
  :linenos:

If you want to catch this error in a specific place
and attach a specific behavior, use an error handler at a proper level.

For example, here we would handle it on a controller level:

.. literalinclude:: /examples/error_handling/pydantic_validation_handled.py
  :caption: views.py
  :language: python
  :linenos:

Now, the error is handled: we modified its error text and status code.
Remember not to dump all the error information out to users,
since they might contain sensitive data.

.. seealso::

  See :ref:`handler500` if you want to change the ``500`` error rendering.


API Reference
-------------

.. autofunction:: dmr.errors.global_error_handler

.. autofunction:: dmr.errors.wrap_handler

.. autoclass:: dmr.errors.ErrorType
  :members:

.. autoclass:: dmr.errors.ErrorModel
  :members:

.. autoclass:: dmr.errors.ErrorDetail
  :members:

.. autofunction:: dmr.errors.format_error


Problem Details API
~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.problem_details.ProblemDetailsError
  :members:
  :show-inheritance:

.. autoclass:: dmr.problem_details.ProblemDetailsModel
  :members:
