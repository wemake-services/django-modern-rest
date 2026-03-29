Streaming
=========

What is a stream?
-----------------

Streaming is a bit different from a regular REST APIs.
REST APIs always returns the whole data in its response.

Streaming establishes a persistent connection,
accepts headers with the content type
of ``application/jsonl`` (stands for "JSON Lines") or ``text/event-stream``
and then streams each individual event when it is ready one by one.

.. mermaid::
  :caption: How streaming works
  :config: {"theme": "forest"}

  sequenceDiagram
      participant App
      participant Client

      Client->>App: Make the initial request
      App->>Client: Establish connection and send headers

      App->>App: Produce Event 1
      App->>Client: Send Event 1
      Client->>Client: Process Event 1

      App->>App: Produce Event 2
      App->>Client: Send Event 2
      Client->>Client: Process Event 2

      Note over App: Continue producing events...
      Note over Client: Continue consuming events...

      Client->>App: Closes the connection
      App->>App: Cleans everything up


When to use streaming? When you have a single-directional stream of events.

For example:

- LLM responses
- Logs
- Telemetry
- Financial services
- Sporting events
- Live locations

**Do not** use streaming for regular responses with regular data.
Only use it when needed.


Just a regular controller
-------------------------

We base our API around :class:`dmr.streaming.controller.StreamingController`
type which is a slightly modified subclass
of a regular :class:`~dmr.controller.Controller`.

Streaming controllers support all the same features:

- Different HTTP async or sync methods
- :doc:`Components parsing <../components/index>`
- :doc:`../auth/common`
- :doc:`../error-handling` (including special error handling for events)
- :doc:`../negotiation`
- Optional :ref:`response_validation` (including events validation)
- etc

We utilize :class:`collections.abc.AsyncIterator`
protocol to model async event sources.


Existing streaming formats
--------------------------

We support:

.. tabs::

  .. tab:: JsonLines

    JsonLines is a simple format, where events are streamed line by line,
    and all lines are valid JSON objects.

    Read more: :doc:`jsonl`

    .. literalinclude:: /examples/streaming/jsonl/usage_modify.py
      :language: python
      :caption: views.py
      :linenos:

  .. tab:: SSE

    Server Sent Events is very similar: you can put any data in ``data:``
    field, but it has more semantics and is more customizable.

    Read more: :doc:`sse`

    .. literalinclude:: /examples/streaming/sse/usage_modify.py
      :language: python
      :caption: views.py
      :linenos:

What happens in these examples?

1. We create our controller as usual, except we are using
   :class:`dmr.streaming.controller.StreamingController` subtypes
   instead of a regular ``Controller`` class
2. We return :class:`typing.AsyncIterator` instance
   instead of a single data item

Choose the one that fits your needs, or create your own format!

.. important::

  All streaming modes require Django to run
  in `ASGI mode in production <https://docs.djangoproject.com/en/6.0/howto/deployment/asgi>`_.


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

.. tabs::

  .. tab:: JsonLines

    .. literalinclude:: /examples/streaming/jsonl/error_handling.py
      :language: python
      :caption: views.py
      :linenos:

  .. tab:: SSE

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

.. seealso::

  Response disconnect docs: https://docs.djangoproject.com/en/stable/ref/request-response/#request-response-streaming-disconnect


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


Further reading
---------------

.. seealso::

  Best practices for working with async iterators and generators in Python:
  https://docs.python.org/3.15/library/asyncio-dev.html#asynchronous-generators-best-practices

.. grid:: 2 2 2 2
  :class-row: surface
  :padding: 0
  :gutter: 2

  .. grid-item-card:: JsonLines
    :link: jsonl
    :link-type: doc

    Streaming individual lines of json.

  .. grid-item-card:: SSE
    :link: sse
    :link-type: doc

    Streaming Server Sent Events.


Advanced topics
---------------

Negotiation for different formats
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you need different event formats for different users / usecases,
then you can use the regular :doc:`../negotiation` process.

Send different ``Accept`` headers to get different event streams back:

.. literalinclude:: /examples/streaming/streaming_negotiaion.py
  :language: python
  :caption: views.py
  :linenos:

This is a really advanced feature that is not required in 99% of cases.
Here we define our own :class:`~dmr.streaming.controller.StreamingController`
subclass and override a special method to instantiate streaming renderers
:meth:`~dmr.streaming.controller.StreamingController.streaming_renderers`.

Next we define an API endpoint for ``GET`` method.
We use :func:`~dmr.negotiation.conditional_type` function to specify which
type will be returned in which case for the OpenAPI metadata.

And ``_event_source()`` method which will provide events for both of the formats.

The last thing we do is we check what ``Accept`` header
we are working with and provide an appropriate format for each case.


API Reference
-------------

Controllers
~~~~~~~~~~~

.. autoclass:: dmr.streaming.controller.StreamingController
  :members:

Responses
~~~~~~~~~

.. autoclass:: dmr.streaming.stream.StreamingResponse
  :members:

Renderers
~~~~~~~~~

.. autoclass:: dmr.streaming.renderer.StreamingRenderer
  :members:

Validation
~~~~~~~~~~

.. autoclass:: dmr.streaming.validation.StreamingValidator
  :members:

.. autofunction:: dmr.streaming.validation.validate_event_type
