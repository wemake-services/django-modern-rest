Server Sent Events
==================

Standard: https://html.spec.whatwg.org/multipage/server-sent-events.html

Our ``SSE`` implementation allows users to follow the standard above
or fully customize the experience for custom needs.


Using SSE
---------

You can use SSE with both :func:`~dmr.endpoint.validate`
and :func:`~dmr.endpoint.modify` style endpoints:

.. tabs::

  .. tab:: modify

    .. literalinclude:: /examples/streaming/sse/usage_modify.py
      :language: python
      :caption: views.py
      :linenos:

  .. tab:: validate

    .. literalinclude:: /examples/streaming/sse/usage_validate.py
      :language: python
      :caption: views.py
      :linenos:


What happens in these examples?

1. We define an event producing method ``produce_user_events``
   yielding events one by one.
   It returns an :class:`collections.abc.AsyncIterator` instance
2. It must produce instances of :class:`dmr.streaming.sse.metadata.SSEvent`,
   which will be rendered into the stream
3. We define a special :class:`~dmr.streaming.sse.controller.SSEController`
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

.. note::

  Note that default ``EventSource`` JavaScript API only support
  headers, cookies, query, and path parameters in ``GET`` HTTP method.

  Custom implementations might use any HTTP methods and any type of parameters.

For example, if you need to parse ``Last-Event-ID`` header
(which is a part of the default ``EventSource`` spec and API):

.. literalinclude:: /examples/streaming/sse/components.py
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

SSE endpoints can also be protected by any instance of the async auth.
However, note that default ``EventSource`` JavaScript API
does not support passing explicit headers. There are several options:

1. Cookies based auth, because ``EventSource`` passes
   all the cookies on the request
2. Query string based auth, but it might be exposed in logs / etc,
   so make sure tokens have a really short expiration time
3. Using your own ``EventSource``

Here's an example with
:class:`~dmr.security.django_session.auth.DjangoSessionAsyncAuth` class:

.. literalinclude:: /examples/streaming/sse/auth.py
   :language: python
   :caption: views.py
   :linenos:

If you don't use ``EventSource`` API, you can use any other auth
of your choice, all of them will just work.

.. seealso::

  Read our :doc:`../auth/common` guide.


Serializing events
------------------

Our default class :class:`~dmr.streaming.sse.metadata.SSEvent`
supports two modes:

- Passing ``serialize=True`` (default) for all event bodies,
  so they will be serialized with the serializer from the controller.
  In this mode you can pass any objects that are supported by your serializer
- Or passing ``serialize=False`` alongside the existing :class:`bytes` object.
  It won't trigger any extra serialization.
  It might be useful if you already have some existing binary data


Modeling business events
------------------------

We provide our default implementation for sending events:
:class:`~dmr.streaming.sse.metadata.SSEvent`

But, users are not required to use it directly.
They can create their own models, as long as they respect
:class:`~dmr.streaming.sse.metadata.SSE` protocol fields.

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

.. literalinclude:: /examples/streaming/sse/event_modeling.py
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

  Use :func:`dmr.streaming.sse.validation.check_event_field` to do that.


Best practices
--------------

``django-modern-rest`` implements a bunch of best practices for streaming SSE:

- ``Connection: keep-alive`` header keeps the connection open
- ``Cache-Control: no-cache`` header prevents caching the stream response
- ``X-Accel-Buffering: no`` header prevents `proxy response buffering
  <https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering>`_
  in some proxy servers like Nginx
- Every 15 seconds we send ``: ping`` keep-alive events,
  when there hasn't been any message,
  to prevent some servers from closing the connection as inactive.
  This is a direct recommendation from `the SSE spec <https://html.spec.whatwg.org/multipage/server-sent-events.html#authoring-notes>`_


Everything just works out of the box, you don't have to do anything.


API Reference
-------------

Controller
~~~~~~~~~~

.. autoclass:: dmr.streaming.sse.controller.SSEController
  :members:
  :show-inheritance:

Metadata
~~~~~~~~

.. autoclass:: dmr.streaming.sse.metadata.SSE
  :members:

.. autoclass:: dmr.streaming.sse.metadata.SSEvent
  :members:

Renderer
~~~~~~~~

.. autoclass:: dmr.streaming.sse.renderer.SSERenderer
  :members:

Validation
~~~~~~~~~~

.. autoclass:: dmr.streaming.sse.validation.SSEStreamingValidator
  :members:
  :show-inheritance:

.. autofunction:: dmr.streaming.sse.validation.validate_event_data

.. autofunction:: dmr.streaming.sse.validation.check_event_field

Exceptions
~~~~~~~~~~

.. autoexception:: dmr.streaming.exceptions.StreamingCloseError
  :members:
