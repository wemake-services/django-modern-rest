Content negotiation
===================

.. autoclass:: dmr.negotiation.RequestNegotiator
  :members:

.. autoclass:: dmr.negotiation.ResponseNegotiator
  :members:

.. autoclass:: dmr.negotiation.ContentType
  :members:

.. autofunction:: dmr.negotiation.conditional_type

.. autofunction:: dmr.negotiation.request_parser

.. autofunction:: dmr.negotiation.request_renderer

.. autofunction:: dmr.negotiation.get_conditional_types


Parser API
----------

.. autoclass:: dmr.parsers.Parser
  :members:


Renderer API
------------

.. autoclass:: dmr.renderers.Renderer
  :members:


Existing parsers and renderers
------------------------------

Parsers
~~~~~~~

.. autoclass:: dmr.plugins.msgspec.MsgspecJsonParser
  :members:

.. autoclass:: dmr.plugins.msgspec.MsgpackParser
  :members:

.. autoclass:: dmr.parsers.JsonParser
  :members:

.. autoclass:: dmr.parsers.MultiPartParser
  :members:

.. autoclass:: dmr.parsers.FormUrlEncodedParser
  :members:

Renderers
~~~~~~~~~

.. autoclass:: dmr.plugins.msgspec.MsgspecJsonRenderer
  :members:

.. autoclass:: dmr.plugins.msgspec.MsgpackRenderer
  :members:

.. autoclass:: dmr.renderers.JsonRenderer
  :members:

.. autoclass:: dmr.renderers.FileRenderer
  :members:


Advanced API
------------

.. autoclass:: dmr.parsers.SupportsFileParsing
  :members:

.. autoclass:: dmr.parsers.SupportsDjangoDefaultParsing
  :members:
