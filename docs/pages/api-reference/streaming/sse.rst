Server Sent Events
==================

Server-sent events
------------------

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

.. autofunction:: dmr.streaming.sse.validation.validate_event_fields

.. autofunction:: dmr.streaming.sse.validation.check_event_field

Exceptions
~~~~~~~~~~

.. autoexception:: dmr.streaming.exceptions.StreamingCloseError
  :members:
