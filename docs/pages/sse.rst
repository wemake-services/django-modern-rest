Server Sent Events aka SSE
==========================

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

We utilize :class:`typing.AsyncIterator` protocol to model event sources.

.. literalinclude:: /examples/sse/usage.py
   :language: python
   :linenos:


Using components
----------------

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
:class:`~dmr.security.django_session.DjangoSessionAsyncAuth` class:

.. literalinclude:: /examples/sse/error_handling.py
   :language: python
   :linenos:

You can customize :class:`~dmr.security.jwt.JWTAsyncAuth`
to provide auth in cookies instead of headers.
This way you will be able to send the same JWT tokens
to establish trusted SSE connection.

You would need to:

- Customize :attr:`~dmr.security.jwt.JWTSyncAuth.security_requirement`
  property to change how your security requirement in defined in OpenAPI
- Customize :meth:`~dmr.security.jwt.JWTAsyncAuth.get_token_from_request`
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
nside the events producing async iterator.

Handling disconnects
~~~~~~~~~~~~~~~~~~~~

Async clients can disconnect at any time using :exc:`asyncio.CancelledError`.
It is a good idea to handle this error.

See Django docs: https://docs.djangoproject.com/en/6.0/ref/request-response/#request-response-streaming-disconnect


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
It defaults to the passed ``validate_responses`` value.

.. literalinclude:: /examples/sse/event_validation.py
   :language: python
   :linenos:

However, it is recommended to use event validation in development
and to disable it in production.
You can do so by setting :data:`~dmr.settings.Settings.validate_responses`
to ``False`` in production. It will also disable ``validate_events`` as well.


API Reference
-------------

Builder
~~~~~~~

.. autofunction:: dmr.sse.builder.sse

Metadata
~~~~~~~~

.. autodata:: dmr.sse.metadata.SSEData

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

Exceptions
~~~~~~~~~~

.. autoexception:: dmr.sse.exceptions.SSECloseConnectionError
