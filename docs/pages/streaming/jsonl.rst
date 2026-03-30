Json Lines
==========

Standard: https://jsonlines.org

Our ``jsonl`` implementation allows users to follow the standard above.


Using JsonLines
---------------

You can use JsonLines format with both :func:`~dmr.endpoint.validate`
and :func:`~dmr.endpoint.modify` style endpoints:

.. tabs::

  .. tab:: modify

    .. literalinclude:: /examples/streaming/jsonl/usage_modify.py
      :language: python
      :caption: views.py
      :linenos:

  .. tab:: validate

    .. literalinclude:: /examples/streaming/jsonl/usage_validate.py
      :language: python
      :caption: views.py
      :linenos:


What happens in these examples?

1. We define an event producing method ``produce_user_events``
   yielding events one by one.
   It returns an :class:`collections.abc.AsyncIterator` instance
2. It must produces instances of objects that can be serialized to ``json``
   with a serializer of your choice. These events will be renderer into a stream
3. We define a special
   :class:`~dmr.streaming.jsonl.controller.JsonLinesController`
   class that has regular ``get`` HTTP endpoint. In ``@modify`` example
   it returns the async generator directly, while in ``@validate`` example
   it returns the :class:`dmr.streaming.stream.StreamingResponse` instance
4. Next, ASGI will take the returned data and stream events to your users

.. seealso::

  - Async Generators in Python: https://peps.python.org/pep-0525
  - Streaming in ASGI: https://asgi.readthedocs.io/en/latest/specs/main.html

.. important::

  Our streaming implementation will not work with a WSGI handler in production.
  Why? Because streaming is a long-living connection by design.
  WSGI handlers have very limited number of connections.
  Basically ``number_of_workers * number_of_threads``,
  just a very small number of streaming clients will completely
  block all other work on the server.

  **Use ASGI** for all streaming endpoints.
  This will give you the best of two worlds: simple sync Django
  for the major part of your code base and some async endpoints where you need them.
  See our :doc:`guide <../structure/sync-and-async>`.

  However, we allow running streaming with WSGI
  if ``settings.DEBUG is True`` for local development and testing.
  In a very *limited* compatibility mode.


Using components
----------------

If you want to parse any incoming data,
you can do it the same way as in any other controller.

JsonL supports passing any type of data to the endpoint.

.. literalinclude:: /examples/streaming/jsonl/components.py
   :language: python
   :caption: views.py
   :linenos:

We are using a regular approach
with the :data:`~dmr.components.Headers` component.

.. note::

  Use ``Last-Event-ID`` header to handle reconnects to start sending
  events to the client from the last consumed one.

.. seealso::

  Read our :doc:`../components/index` guide.


Auth
----

JsonL endpoints fully support any style of auth that you might need.

Here's an example with
:class:`~dmr.security.jwt.auth.JWTAsyncAuth` class:

.. literalinclude:: /examples/streaming/jsonl/auth.py
   :language: python
   :caption: views.py
   :linenos:

.. seealso::

  Read our :doc:`../auth/common` guide.


Best practices
--------------

``django-modern-rest`` implements a bunch of best practices for streaming SSE:

- ``Connection: keep-alive`` header keeps the connection open
- ``Cache-Control: no-cache`` header prevents caching the stream response
- ``X-Accel-Buffering: no`` header prevents `proxy response buffering
  <https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering>`_
  in some proxy servers like Nginx

Everything just works out of the box, you don't have to do anything.
However, we don't send ``ping`` events by default, because the format
for them is not well defined in ``jsonl``.

You can enable them by changing
:attr:`~dmr.streaming.controller.StreamingController.streaming_ping_seconds`
to the maximum number of second before the ``ping`` event happens.
And :meth:`~dmr.streaming.controller.StreamingController.ping_event`
for the event payload.


API Reference
-------------

Controller
~~~~~~~~~~

.. autoclass:: dmr.streaming.jsonl.controller.JsonLinesController
  :members:
  :show-inheritance:

Renderer
~~~~~~~~

.. autoclass:: dmr.streaming.jsonl.renderer.JsonLinesRenderer
  :members:

Validation
~~~~~~~~~~

.. autoclass:: dmr.streaming.jsonl.validation.JsonLinesStreamingValidator
  :members:
  :show-inheritance:
