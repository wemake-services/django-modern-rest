Error handling
==============

``django-modern-rest`` has 3 layers where errors might be handled.
It provides flexible error handling logic
on :class:`~django_modern_rest.endpoint.Endpoint`,
:class:`~django_modern_rest.controller.Controller`,
and :func:`global <django_modern_rest.errors.global_error_handler>` levels.

Here's how it works:

1. We first try to call ``error_handler`` that was passed into the endpoint
   definition via :func:`~django_modern_rest.endpoint.modify`
   or :func:`~django_modern_rest.endpoint.validate`
2. If it returns :class:`django.http.HttpResponse`, just return it to the user
3. If it raises, call
   :meth:`~django_modern_rest.controller.Controller.handle_error` for sync
   controllers
   and :meth:`~django_modern_rest.controller.Controller.handle_async_error`
   for async controllers
4. If controller's handler returns :class:`~django.http.HttpResponse`,
   just return it to the user
5. If it raises, call configured global error handler, by default
   it is :func:`~django_modern_rest.errors.global_error_handler`
   (it is always sync)

.. warning::

  There are two things to keep in mind:

  1. Async endpoints will require async ``error_handler`` parameter,
     Sync endpoints will require sync ``error_handler`` parameter.
     This is validated on endpoint creation
  2. :meth:`~django_modern_rest.controller.Controller.handle_error`
     won't be called for async controllers.
     And :meth:`~django_modern_rest.controller.Controller.handle_async_error`
     won't be called for sync ones.

.. note::

  :exc:`~django_modern_rest.response.APIError` does not follow any of these
  rules and has a default handler, which will convert an instance
  of ``APIError`` to :class:`~django.http.HttpResponse` via
  :meth:`~django_modern_rest.controller.Controller.to_error` call.

  You don't need to catch ``APIError`` in any way,
  unless you know what you are doing.


Customizing endpoint error handler
----------------------------------

Let's pass custom error handling to a single endpoint:

.. literalinclude:: /examples/error_handling/endpoint.py
  :caption: views.py
  :linenos:
  :lines: 17-

In this example we add error handling defined as ``division_error``
to ``get`` endpoint (which serves as a division operation),
while keeping ``post`` endpoint (which serves as a multiply operation)
without a custom error handler.
Because :exc:`ZeroDivisionError` can't happen in ``post``.

Per-endpoint's error handling has a priority over per-controller handlers.


Customizing controller error handler
------------------------------------

Let's create custom error handling for the whole controller:

.. literalinclude:: /examples/error_handling/controller.py
  :caption: views.py
  :linenos:
  :lines: 18-

In this example we define ``async_error_handler`` for both endpoints.
All ``httpx.HTTPError`` errors that can happen in both endpoints
will be safely handled. Notice that we also add new response schema
to :attr:`~django_modern_rest.controller.Controller.responses`
to be sure that it will be present in the OpenAPI
and response validation will work.


Going further
-------------

Now you can understand how you can create:

- Endpoints with custom error handlers
- Controllers with custom error handlers
- :class:`~django_modern_rest.response.ResponseDescription` objects
  for new error response schemas

You can dive even deeper and:

- Subclass :attr:`~django_modern_rest.controller.Controller`
  and provide default error handling for this specific subclass
- Redefine :attr:`~django_modern_rest.controller.Controller.endpoint_cls`
  and change how one specific endpoint behaves on a deep level,
  see :meth:`~django_modern_rest.endpoint.Endpoint.handle_error`
  and :meth:`~django_modern_rest.endpoint.Endpoint.handle_async_error`


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
