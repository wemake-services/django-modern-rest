Content negotiation
===================

``django_modern_rest`` supports content negotiation by default.
As well as writing custom parsers and renderers.

We have two abstractions to do that:

- Parsers: subtypes of :class:`~django_modern_rest.parsers.Parser` type
  that parses request body based on
  `Content-Type <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Type>`_
  header into python primitives

- Renderers: subtypes of :class:`~django_modern_rest.renderers.Renderer` type
  that renders python primitives into a requested format
  based on the
  `Accept <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Accept>`_
  header

By default ``json`` parser and renderer are configured
to use ``msgspec`` if it is installed (recommended).
Or to fallback to pure-python implementation if it is not installed.


How parser and renderer are selected
------------------------------------

We select :class:`~django_modern_rest.parsers.Parser` subtype
if there's a :class:`~django_modern_rest.components.Body` to parse.
Otherwise, for performance reasons, no parser is selected
and body is not parsed.

Here's how we select a parser, when it is needed:

1. We look at the ``Content-Type`` header
2. If it is not provided, we take the default parser,
   which is the last specified parser type for the endpoint,
   aka the most specific one
3. If there's a ``Content-Type`` header,
   we try to exactly match known parsers based on their
   :attr:`~django_modern_rest.parsers.Parser.content_type` attribute
4. If no parser fits the requested content type, we raise
   :exc:`~django_modern_rest.exceptions.RequestSerializationError`

We select :class:`~django_modern_rest.renderers.Renderer` subtype
for all responses (including error responses).
We do that at the very end of the request/response cycle.

Here's how we select a renderer:

1. We look at ``Accept`` header
2. If it is not provided, we take the default renderer,
   which is the last specified renderer type for the endpoint,
   aka the most specific one
3. If there's an ``Accept`` header,
   we use :meth:`django.http.HttpRequest.get_preferred_type` method
   to match the best accepted type, based on order, weights, etc
4. If no renderer fits for the accepted content types, we raise
   :exc:`~django_modern_rest.exceptions.ResponseSerializationError`

.. important::

  Settings always must have one parser and one renderer types defined,
  because utils like :func:`django_modern_rest.response.build_response`
  fallback to settings-defined types only, because they don't have
  an access to the current endpoint.


Customizing negotiation process
-------------------------------

.. note::

  If you only use ``json`` API - there's no need to change anything.

However, if you want to support other formats like ``xml`` or custom ones,
you can write and configure your own parsers and renderers.

Parsers and renderers might be defined on different levels.
Here are all the possible ways starting with the most specific one,
going back to the less specific:

.. tabs::

    .. tab:: per endpoint

      .. literalinclude:: /examples/negotiation/per_endpoint.py
        :caption: views.py
        :linenos:
        :emphasize-lines: 35

    .. tab:: per blueprint

      .. literalinclude:: /examples/negotiation/per_blueprint.py
        :caption: views.py
        :linenos:
        :emphasize-lines: 38-39

    .. tab:: per controller

      .. literalinclude:: /examples/negotiation/per_controller.py
        :caption: views.py
        :linenos:
        :emphasize-lines: 37-38

    .. tab:: per settings

      .. literalinclude:: /examples/negotiation/settings.py
        :caption: settings.py
        :linenos:
        :emphasize-lines: 5-6

You can also modify
:attr:`django_modern_rest.endpoint.Endpoint.request_negotiator_cls`
and :attr:`django_modern_rest.endpoint.Endpoint.response_negotiator_cls`
to completely change the negotiation logic to fit your needs.

This is possible on per-controller level.


Writing custom parsers and renderers
------------------------------------

And here's how our test ``xml`` parser and renderer are defined:

.. literalinclude:: /examples/negotiation/negotiation.py
   :caption: negotiation.py
   :linenos:


Negotiation API
---------------

.. autoclass:: django_modern_rest.negotiation.RequestNegotiator
  :members:

.. autoclass:: django_modern_rest.negotiation.ResponseNegotiator
  :members:

.. autoclass:: django_modern_rest.negotiation.ContentType
  :members:

.. autofunction:: django_modern_rest.negotiation.content_negotiation

.. autofunction:: django_modern_rest.negotiation.request_parser

.. autofunction:: django_modern_rest.negotiation.request_renderer


Parser API
----------

.. autoclass:: django_modern_rest.parsers.Parser
  :members:


Renderer API
------------

.. autoclass:: django_modern_rest.renderers.Renderer
  :members:


Existing parsers and renderers
------------------------------

.. autoclass:: django_modern_rest.plugins.msgspec.MsgspecJsonParser
  :members:

.. autoclass:: django_modern_rest.plugins.msgspec.MsgspecJsonRenderer
  :members:

.. autoclass:: django_modern_rest.parsers.JsonParser
  :members:

.. autoclass:: django_modern_rest.renderers.JsonRenderer
  :members:
