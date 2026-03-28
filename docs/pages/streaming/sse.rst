Server Sent Events
==================

Standard: https://html.spec.whatwg.org/multipage/server-sent-events.html

Our SSE implementation allows users to follow the standard above
or fully customize the experience for custom needs.


Using SSE
---------

When to use SSE? When you have a single directional stream of events.
These events are sent over a single HTTP connection.

We base our API around :class:`dmr.streaming.sse.controller.SSEController`
type which is a slightly modified subclass
of a regular :class:`~dmr.controller.Controller`.

Streaming controllers support all the same features:

- Different HTTP async or sync methods
- Components parsing
- Auth
- Error handling (including special error handling for events)
- Optional response validation (including events validation)
- etc

We utilize :class:`collections.abc.AsyncIterator`
protocol to model event sources.

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
2. It must produces instances of :class:`dmr.streaming.sse.metadata.SSEvent`,
   which will be renderer into the stream
3. We define a special :class:`~dmr.streaming.sse.controller.SSEController`
   class that has regular ``get`` HTTP endpoint. In ``@modify`` example
   it returns the async generator directly, while in ``@validate`` example
   it returns the :class:`dmr.streaming.stream.StreamingResponse` instance
4. Next, ASGI will take the returned data and stream events to your users

.. seealso::

  - Async Generators in Python: https://peps.python.org/pep-0525
  - Streaming in ASGI: https://asgi.readthedocs.io/en/latest/specs/main.html

.. important::

  Our SSE implementation will not work with a WSGI handler in production.
  Why? Because SSE is a long-living connection by design.
  WSGI handlers have very limited number of connections.
  Basically ``number_of_workers * number_of_threads``,
  just a very small number of SSE clients will completely
  block all other work on the server.

  **Use ASGI** for SSE endpoints.
  This will give you the best of two worlds: simple sync Django
  for the major part of your code base and some async endpoints where you need them.
  See our :doc:`guide <../structure/sync-and-async>`.

  However, we allow running SSE with WSGI
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


Handling errors
---------------

Streaming controllers have two layers of error handling:

1. Default error handling works the same way for request / response
   phase, see :doc:`../error-handling` for more information
2. Per-event error handling, which starts when the streaming connection
   is established and the events are produced.
   Such errors are handled in
   :meth:`~dmr.streaming.controller.StreamingController.handle_event_error`
   method

The second layer of event error handling is unique
for streaming controllers.

It works for several cases:

1. When event validation fails (mostly useful in development)
2. When there's an error in the event producer

Let's see how it can be customized.

.. literalinclude:: /examples/streaming/sse/error_handling.py
   :language: python
   :caption: views.py
   :linenos:

.. warning::

  Please, note that new events won't be produced if the error happens
  in the async generator itself. If you want to handle errors there as well,
  use ``try/except`` right inside the event producing async generator.

Handling disconnects
~~~~~~~~~~~~~~~~~~~~

If you need to immediately close the response stream, you can raise
:exc:`~dmr.streaming.exceptions.StreamingCloseError`
or :exc:`asyncio.CancelledError`
inside the events producing async iterator.

Async clients can disconnect at any time.
We always handle this error gracefully.

See Django docs: https://docs.djangoproject.com/en/stable/ref/request-response/#request-response-streaming-disconnect


Validation
----------

All our regular :ref:`response validation rules <response_validation>`
are applied to the SSE controllers as well.
We strictly validate that all headers / cookies / etc
are listed in the endpoint's metadata.

We follow the regular rules for response validation and it can be disabled
by setting ``validate_responses=False`` on the needed level.

We also validate **events structure**, when streaming them to end users.
It is recommended to be turned on in development and turned off in production.

Rules:

- If endpoint specified ``validate_events`` boolean value, we use it
- If endpoint does not specify this flag, but controller does, we use it
- If controller does not specify this flag, but settings does, we use it
- If no explicit ``validate_events`` boolean value is specified, we fallback
  to ``validate_responses`` value

.. tabs::

    .. tab:: per endpoint

        Both  :func:`~dmr.endpoint.validate` and :func:`~dmr.endpoint.modify`
        support this flag:

        .. literalinclude:: /examples/streaming/sse/per_endpoint.py
          :language: python
          :caption: views.py
          :linenos:

    .. tab:: per controller

        .. literalinclude:: /examples/streaming/sse/per_controller.py
          :language: python
          :caption: views.py
          :linenos:

    .. tab:: per settings

        See :data:`~dmr.settings.Settings.validate_events` setting.

        .. code-block:: python
          :caption: settings.py

          >>> from dmr.settings import Settings

          >>> DMR_SETTINGS = {Settings.validate_events: False}


How does we know the model for events to be validated against?

- It might be specified as the ``return_type``
  in the :class:`~dmr.metadata.ResponseSpec` of ``@validate``
  for the given status code
- It might be specified as the type argument to generic
  :class:`collections.abc.AsyncIterator` return type
  in ``@modify`` styled endpoint.

We fallback to :data:`typing.Any` if we can't inference the event model.


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
