Server Sent Events aka SSE
==========================

Standard: https://html.spec.whatwg.org/multipage/server-sent-events.html

.. important::

  Our SSE implementation will not work with WSGI handler in production.
  Why? Because SSE is a long-living connection by design.
  WSGI handlers have very limited amount of connections.
  Basically ``number_of_workers * number_of_threads``,
  just a very small number of SSE clients will completely
  block all other work on the sever.

  Use ASGI for SSE endpoints.
  This will give you the best of two worlds: simple sync Django
  for major code base and some async endpoints where you need them.

  However, we allow running SSE with WSGI
  if ``settings.DEBUG is True`` for local development.


Usage Guide
-----------


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
