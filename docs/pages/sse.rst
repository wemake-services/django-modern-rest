Server Sent Events
==================

Standard: https://html.spec.whatwg.org/multipage/server-sent-events.html

.. important::

  Our SSE implementation will not work with WSGI handler in production.
  Why? Because SSE is a long-living connection by design.
  WSGI handlers have very limited amount of connections.
  Basically ``number_of_workers * number_of_threads``,
  just a very small number of SSE clients will completely
  block all other work on the server.

  **Use ASGI** for SSE endpoints.
  This will give you the best of two worlds: simple sync Django
  for major part of your code base and some async endpoints where you need them.
  See our :doc:`guide <structure/sync-and-async>`.

  However, we allow running SSE with WSGI
  if ``settings.DEBUG is True`` for local development and testing.
  In a very *limited* compatibiltity mode.


Using SSE
---------

When to use SSE? When you have a single directional stream of events.
These events are sent over a single HTTP connection.

We utilize :class:`collections.abc.AsyncIterator`
protocol to model event sources.

.. literalinclude:: /examples/sse/usage.py
   :language: python
   :linenos:


What happens in this example?

1. We define an event producing function yielding events one by one.
   This functions returns :class:`collections.abc.AsyncIterator` instance
2. We define an async callback for a special :class:`~dmr.controller.Controller`
   instance that we generate inside :deco:`~dmr.sse.builder.sse` decorator
3. This callback must always return :class:`~dmr.sse.metadata.SSEResponse`
   instance. You can set custom headers and cookies on this response as well
4. ``SSEResponse[SSEvent[_User]]`` annotation here does two things.
   First, it is used as a validation model,
   to be sure that all events follow the same model.
   Second, it is used to generate OpenAPI schema for this specific endpoint


Using components
----------------

If you want to parse any incoming data,
we utilize the same parsing components, as a regular API.

:func:`~dmr.sse.builder.sse` supports working with several component types:

- :class:`~dmr.components.Path`
- :class:`~dmr.components.Query`
- :class:`~dmr.components.Headers`
- :class:`~dmr.components.Cookies`

For example, if you need to parse ``Last-Event-ID`` header:

.. literalinclude:: /examples/sse/components.py
   :language: python
   :linenos:

Use :class:`~dmr.sse.metadata.SSEContext` to get parsed
data inside your callback function.
It is also fully annotated with 4 type variables,
which of them have ``None`` as a default value (matches runtime behavior).

.. note::

  Use ``Last-Event-ID`` header to handle reconnects to start sending
  events to the client from the last consumed one.


Auth
----

SSE endpoints can also be protected by any instance of the async auth.
However, note that ``EventSource`` JavaScript API does not support passing
explicit headers. There are several options:

1. Cookies based auth, because ``EventSource`` passes
   all the cookies on the request
2. Query string based auth, but it might be exposed in logs / etc,
   so make sure tokens have a really short expiration time

Here's an example with
:class:`~dmr.security.django_session.auth.DjangoSessionAsyncAuth` class:

.. literalinclude:: /examples/sse/error_handling.py
   :language: python
   :linenos:

You can customize :class:`~dmr.security.jwt.auth.JWTAsyncAuth`
to provide auth in cookies instead of headers.
This way you will be able to send the same JWT tokens
to establish trusted SSE connection.

You would need to:

- Customize :attr:`~dmr.security.jwt.auth.JWTSyncAuth.security_requirement`
  property to change how your security requirement in defined in OpenAPI
- Customize :meth:`~dmr.security.jwt.auth.JWTAsyncAuth.get_token_from_request`
  to get JWT token from the request cookies instead of request's headers


Handling errors
---------------

Any errors which happens in event producers are not handled by default.
Because these errors happen inside the ASGI handler, long after
we can possibly handle them with regular :doc:`error-handling`.

So, any errors that need to be handled, are up to users to handle:

.. literalinclude:: /examples/sse/error_handling.py
   :language: python
   :linenos:

If you need to imediatelly close the response stream, you can raise
:exc:`~dmr.sse.exceptions.SSECloseConnectionError`
inside the events producing async iterator.

Handling disconnects
~~~~~~~~~~~~~~~~~~~~

Async clients can disconnect at any time using :exc:`asyncio.CancelledError`.
It is a good idea to handle this error.

See Django docs: https://docs.djangoproject.com/en/stable/ref/request-response/#request-response-streaming-disconnect


Validation
----------

All our regular :ref:`response validation rules <response_validation>`
are applied to the SSE responses as well.
We strictly validate that all headers / cookies / etc
are listed in the metadata.

It can be disabled by:

- Passing ``validate_responses=False`` parameter
- Or setting :data:`dmr.settings.Settings.validate_responses`
  to ``False`` in the settings file

.. literalinclude:: /examples/sse/response_validation.py
   :language: python
   :linenos:

Users can also disable event structure validation.
By explicitly passing ``validate_events=False`` parameter.
If not passed, it defaults to the passed ``validate_responses`` value.

By default all events are strictly validated:

.. literalinclude:: /examples/sse/event_validation.py
   :language: python
   :linenos:

Now, let's disable it:

.. literalinclude:: /examples/sse/event_validation_disabled.py
   :language: python
   :linenos:
   :emphasize-lines: 13

However, it is recommended to use event validation in development
and to disable it in production.
You can do so by setting :data:`~dmr.settings.Settings.validate_responses`
to ``False`` in production. It will also disable ``validate_events`` as well.


Modeling business events
------------------------

We provide our default implementation for sending events:
:class:`~dmr.sse.metadata.SSEvent`

But, users are not required to use it directly.
They can create their own models, as long as they respect
:class:`~dmr.sse.metadata.SSE` protocol fields.

It is quite common in SSE to model different
`ADTs <https://en.wikipedia.org/wiki/Algebraic_data_type>`_.
Because events can be of different types,
they might have different data based on it.
And they might also contain different other fields based on that.

For example, let's model three different events:

1. If any new users are registered, send us an event with type ``user``,
   ``id`` with the user's id, and a username as the data
2. If any new payment is made, send us ``payment`` event type
   with ``{"amount": int, "currency": str}`` json string as the data
3. Sometimes we send purely technical ``ping`` events
   with ``: ping`` as a comment and ``retry: 50`` instruction

Let's model this with perfect type-safety and state-of-the-art OpenAPI schema.

.. literalinclude:: /examples/sse/event_modeling.py
   :language: python
   :linenos:

This will also generate a correct OpenAPI spec
with all the logical cases covered.

If you are still not happy with the resulting OpenAPI schema,
you can fully customize it using your serializer's official docs.
For example, ``pydantic`` uses ``__get_pydantic_json_schema__`` method
for `this purpose <https://docs.pydantic.dev/latest/concepts/json_schema/#implementing-__get_pydantic_core_schema__>`_.

.. note::

  When creating custom event types, don't forget to validate
  that ``id`` and ``event`` fields do not contain: ``'\x00'``,
  ``'\n'``, and ``'\r'`` chars.

  Use :func:`dmr.sse.validation.check_event_field` to do that.


API Reference
-------------

Builder
~~~~~~~

.. autodecorator:: dmr.sse.builder.sse

Metadata
~~~~~~~~

.. autoclass:: dmr.sse.metadata.SSE
  :members:

.. autoclass:: dmr.sse.metadata.SSEvent
  :members:

.. autoclass:: dmr.sse.metadata.SSEResponse
  :members:

.. autoclass:: dmr.sse.metadata.SSEContext
  :members:

Stream
~~~~~~

.. autoclass:: dmr.sse.stream.SSEStreamingResponse
  :members:


Renderer
~~~~~~~~

.. autoclass:: dmr.sse.renderer.SSERenderer
  :members:

Validation
~~~~~~~~~~

.. autofunction:: dmr.sse.validation.validate_event_type

.. autofunction:: dmr.sse.validation.validate_event_data

.. autofunction:: dmr.sse.validation.check_event_field

Exceptions
~~~~~~~~~~

.. autoexception:: dmr.sse.exceptions.SSECloseConnectionError
