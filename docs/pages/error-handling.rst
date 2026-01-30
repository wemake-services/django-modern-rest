Error handling
==============

``django-modern-rest`` has 3 layers where errors might be handled.
It provides flexible error handling logic
on :class:`~django_modern_rest.endpoint.Endpoint`,
:class:`~django_modern_rest.controller.Controller`,
and :func:`global <django_modern_rest.errors.global_error_handler>` levels.

All error handling functions always accept 3 arguments:

1. :class:`~django_modern_rest.endpoint.Endpoint` where error happened
2. :class:`~django_modern_rest.controller.Controller` where error happened,
   you can also access the :class:`~django_modern_rest.controller.Blueprint`
   where this error happened
   via :attr:`~django_modern_rest.controller.Controller.active_blueprint`
   if it exists
3. Exception that happened

Here's how it works:

1. We first try to call ``error_handler`` that was passed into the endpoint
   definition via :func:`~django_modern_rest.endpoint.modify`
   or :func:`~django_modern_rest.endpoint.validate`
2. If it returns :class:`django.http.HttpResponse`, return it to the user
3. If it raises and :term:`Blueprint` was used to created this endpoint, call
   :meth:`~django_modern_rest.controller.Blueprint.handle_error` for sync
   blueprints
   and :meth:`~django_modern_rest.controller.Blueprint.handle_async_error`
   for async blueprints
4. If blueprint's handler returns :class:`~django.http.HttpResponse`,
   return it to the user
5. If it raises, call
   :meth:`~django_modern_rest.controller.Controller.handle_error` for sync
   controllers
   and :meth:`~django_modern_rest.controller.Controller.handle_async_error`
   for async controllers
6. If controller's handler returns :class:`~django.http.HttpResponse`,
   return it to the user
7. If it raises, call configured global error handler, by default
   it is :func:`~django_modern_rest.errors.global_error_handler`
   (it is always sync)

.. warning::

  There are two things to keep in mind:

  1. Async endpoints will require async ``error_handler`` parameter,
     Sync endpoints will require sync ``error_handler`` parameter.
     This is validated on endpoint creation
  2. We don't allow to define sync ``handle_error`` handlers
     for async blueprints and controllers.
     We also don't allow async ``handle_async_error`` handlers
     for sync controllers.

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
  :language: python
  :linenos:
  :lines: 12-

In this example we add error handling defined as ``division_error``
to ``patch`` endpoint (which serves as a division operation),
while keeping ``post`` endpoint (which serves as a multiply operation)
without a custom error handler.
Because :exc:`ZeroDivisionError` can't happen in ``post``.

Per-endpoint's error handling has a priority
over per-blueprint and per-controller handlers.

You can also define endpoint error handlers as controller methods
and pass them wrapped with :func:`~django_modern_rest.errors.wrap_handler`
as handlers. Like so:

.. literalinclude:: /examples/error_handling/wrap_endpoint.py
  :caption: views.py
  :language: python
  :linenos:
  :lines: 13-


Customizing blueprint error handler
-----------------------------------

Let's create custom error handling for the all endpoints in a blueprint:

.. literalinclude:: /examples/error_handling/blueprint.py
  :caption: views.py
  :language: python
  :linenos:
  :lines: 13-

In this example we define ``async_error_handler`` for both endpoints.
All ``httpx.HTTPError`` errors that can happen in both endpoints
will be safely handled. Notice that we also add new response schema
to :attr:`~django_modern_rest.controller.Blueprint.responses`
to be sure that it will be present in the OpenAPI
and response validation will work.

Per-blueprint's error handling has a priority
over per-controller handlers.

.. note::

  If you are not using blueprints, then this error-handling layer won't exist.


Customizing controller error handler
------------------------------------

Let's create custom error handling for the whole controller:

.. literalinclude:: /examples/error_handling/controller.py
  :caption: views.py
  :language: python
  :linenos:
  :lines: 13-

We do the same as in blueprint's example to show that they are very similar.
The main difference is the priority and scope.


Going further
-------------

Now you can understand how you can create:

- Endpoints with custom error handlers
- Controllers with custom error handlers
- :class:`~django_modern_rest.response.ResponseSpec` objects
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
      EndpointHandler -->|raises| Blueprint[Blueprint-level handler];
      Blueprint --> BlueprintDefinition{Is blueprint used?}
      BlueprintDefinition -->|yes| BlueprintHandler{Raises or returns response?};
      BlueprintDefinition -->|no| Controller;
      BlueprintHandler -->|response| Failure[Error response];
      BlueprintHandler -->|raises| Controller[Controller-level handler];
      Controller --> ControllerHandler{Raises or returns response?};
      ControllerHandler -->|response| Failure[Error response];
      ControllerHandler -->|raises| Global[Global handler];
      Global --> GlobalHandler{Raises or returns response?};
      GlobalHandler -->|response| Failure[Error response];
      GlobalHandler -->|raises| Reraises[Reraises error];
      Error ---->|No| Success[Successful response];


API Reference
-------------

.. autofunction:: django_modern_rest.errors.global_error_handler

.. autofunction:: django_modern_rest.errors.wrap_handler
