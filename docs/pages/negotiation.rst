Content negotiation
===================

``django_modern_rest`` supports content negotiation by default.
As well as writing custom parsers and renderers.


Negotiation API
---------------

.. autoclass:: django_modern_rest.negotiation.RequestNegotiator

.. autoclass:: django_modern_rest.negotiation.ResponseNegotiator

.. autoclass:: django_modern_rest.negotiation.ContentType

.. autofunction:: django_modern_rest.negotiation.content_negotiation

.. autofunction:: django_modern_rest.negotiation.request_parser

.. autofunction:: django_modern_rest.negotiation.request_renderer


Parser API
----------

.. autoclass:: django_modern_rest.parsers.Parser


Renderer API
------------

.. autoclass:: django_modern_rest.renderers.Renderer


Existing parsers and renderers
------------------------------

.. autoclass:: django_modern_rest.plugins.msgspec.MsgspecJsonParser

.. autoclass:: django_modern_rest.plugins.msgspec.MsgspecJsonRenderer

.. autoclass:: django_modern_rest.parsers.JsonParser

.. autoclass:: django_modern_rest.renderers.JsonRenderer
