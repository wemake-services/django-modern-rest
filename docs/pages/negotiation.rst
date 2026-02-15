Content negotiation
===================

``django_modern_rest`` supports content negotiation.

We have two abstractions to do that:

- Parsers: instances of subtypes
  of :class:`~django_modern_rest.parsers.Parser` type
  that parses request body based on
  `Content-Type <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Type>`_
  header into python primitives

- Renderers: instances of subtypes
  of :class:`~django_modern_rest.renderers.Renderer` type
  that renders python primitives into a requested format
  based on the
  `Accept <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Accept>`_
  header

By default ``json`` parser and renderer are configured
to use ``msgspec`` if it is installed (recommended).
We fallback to pure-python implementation if ``msgspec`` is not installed.


How parser and renderer are selected
------------------------------------

We select a :class:`~django_modern_rest.parsers.Parser` instance
if there's a :class:`~django_modern_rest.components.Body`
or :class:`~django_modern_rest.components.FileMetadata` components to parse.
Otherwise, for performance reasons, no parser is selected at all.
Nothing to parse - no parser is selected.

Here's how we select a parser, when it is needed:

1. We look at the ``Content-Type`` header
2. If it is not provided, we take the default parser,
   which is the first specified parser for the endpoint,
   aka the most specific one
3. If there's a ``Content-Type`` header,
   we try to exactly match known parsers based on their
   :attr:`~django_modern_rest.parsers.Parser.content_type` attribute.
   This is a positive path optimization
4. If there's no direct match, we now include parsers
   that have ``*`` pattern in supported content types.
   We match them in order based on ``'specificity', 'quality'``,
   the first match wins
5. If no parser fits the request's content type, we raise
   :exc:`~django_modern_rest.exceptions.RequestSerializationError`

We select :class:`~django_modern_rest.renderers.Renderer` instance
for all responses (including error responses), before performing any logic.
If the selection fails, we don't even try to run the endpoint.

Here's how we select a renderer:

1. We look at ``Accept`` header
2. If it is not provided, we take the default renderer,
   which is the first specified renderer for the endpoint,
   aka the most specific one
3. If there's an ``Accept`` header,
   we use :meth:`django.http.HttpRequest.get_preferred_type` method
   to match the best accepted type, based on ``'specificity', 'quality'``,
   the first match wins
4. If no renderer fits for the accepted content types, we raise
   :exc:`~django_modern_rest.exceptions.ResponseSchemaError`

.. note::

  When constructing response manually, like:

  .. code-block:: python

    >>> from django.http import HttpResponse
    >>> response = HttpResponse(b'[]')

  The renderer is selected as usual, but no actual rendering is done.
  However, all other validation works as expected.

  But, when using :meth:`~django_modern_rest.controller.Controller.to_response`
  method, renderer will be executed.
  So, it is a preferred method for regular responses.

.. important::

  Settings always must have one parser
  and one renderer defined at all times,
  because utils like :func:`django_modern_rest.response.build_response`
  fallbacks to settings-defined renderers in some error cases.


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
        :language: python
        :linenos:
        :emphasize-lines: 35

    .. tab:: per blueprint

      .. literalinclude:: /examples/negotiation/per_blueprint.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 39-40

    .. tab:: per controller

      .. literalinclude:: /examples/negotiation/per_controller.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 39-40

    .. tab:: per settings

      .. literalinclude:: /examples/negotiation/settings.py
        :caption: settings.py
        :language: python
        :linenos:
        :emphasize-lines: 6-7

First parsers / renders definition found, starting from the top,
will win and be used for the endpoint.

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
   :language: python
   :linenos:


Using different schemes for different content types
---------------------------------------------------

Sometimes we have to accept different schemes based on the content type.
`According to the OpenAPI spec <https://swagger.io/docs/specification/v3_0/describing-request-body/describing-request-body/#requestbody-content-and-media-types>`_,
:class:`~django_modern_rest.components.Body`
should support different content types.

We utilize :data:`typing.Annotated`
and :func:`django_modern_rest.negotiation.conditional_type`:

.. literalinclude:: /examples/negotiation/conditional_body_types.py
   :caption: views.py
   :language: python
   :linenos:

We strictly validate that each content type will have its own unique model.
As the last example shows, it is impossible to send ``_XMLRequestModel``
with ``Content-Type: application/json`` header.

The same works for return types as well:

.. literalinclude:: /examples/negotiation/conditional_return_types.py
   :caption: views.py
   :language: python
   :linenos:

Depending on the content type - your return schema
will be fully validated as well.
In the example above, it would be an error to return something other
than ``list[str]`` for ``json`` content type, and it would also
be an error to return anything other than ``dict[str, str]``
for ``xml`` content type.

You can combine conditional bodies and conditional return types
in a type-safe and fully OpenAPI-compatible way.


Negotiation API
---------------

.. autoclass:: django_modern_rest.negotiation.RequestNegotiator
  :members:

.. autoclass:: django_modern_rest.negotiation.ResponseNegotiator
  :members:

.. autoclass:: django_modern_rest.negotiation.ContentType
  :members:

.. autofunction:: django_modern_rest.negotiation.conditional_type

.. autofunction:: django_modern_rest.negotiation.request_parser

.. autofunction:: django_modern_rest.negotiation.request_renderer

.. autofunction:: django_modern_rest.negotiation.get_conditional_types


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

Parsers
~~~~~~~

.. autoclass:: django_modern_rest.plugins.msgspec.MsgspecJsonParser
  :members:

.. autoclass:: django_modern_rest.parsers.JsonParser
  :members:

.. autoclass:: django_modern_rest.parsers.MultiPartParser
  :members:

.. autoclass:: django_modern_rest.parsers.FormUrlEncodedParser
  :members:

Renderers
~~~~~~~~~

.. autoclass:: django_modern_rest.plugins.msgspec.MsgspecJsonRenderer
  :members:

.. autoclass:: django_modern_rest.renderers.JsonRenderer
  :members:

.. autoclass:: django_modern_rest.renderers.FormUrlEncodedParser
  :members:


Advanced API
------------

.. autoclass:: django_modern_rest.parsers.SupportsFileParsing
  :members:

.. autoclass:: django_modern_rest.parsers.SupportsDjangoDefaultParsing
  :members:
