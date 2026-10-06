Streaming
=========

Controllers
-----------

.. autoclass:: dmr.streaming.controller.StreamingController
  :members:
  :show-inheritance:

Endpoint
--------

.. autodata:: dmr.streaming.modify

.. autodata:: dmr.streaming.validate

.. autoclass:: dmr.streaming.Streaming
  :members:

.. autoclass:: dmr.streaming.endpoint.StreamingExtras
  :members:

Responses
---------

.. autoclass:: dmr.streaming.stream.StreamingResponse
  :members:
  :show-inheritance:

Renderers
---------

.. autoclass:: dmr.streaming.renderer.StreamingRenderer
  :members:
  :show-inheritance:

Validation
----------

.. autoclass:: dmr.streaming.validation.StreamingValidator
  :members:

.. autoclass:: dmr.streaming.validation.StreamingResponseValidator
  :members:

.. autofunction:: dmr.streaming.validation.validate_event_type

.. toctree::
   :maxdepth: 1

   sse
   jsonl
