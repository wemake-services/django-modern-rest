Content negotiation
===================

``django_modern_rest`` supports content negotiation.

We have two abstractions to do that:

- Parsers: instances of subtypes
  of :class:`~dmr.parsers.Parser` type
  that parses request body based on
  `Content-Type <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Type>`_
  header into python primitives

- Renderers: instances of subtypes
  of :class:`~dmr.renderers.Renderer` type
  that renders python primitives into a requested format
  based on the
  `Accept <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Accept>`_
  header

By default ``json`` parser and renderer are configured
to use ``msgspec`` if it is installed (recommended).
We fallback to pure-python implementation if ``msgspec`` is not installed.


How parser and renderer are selected
------------------------------------

We select a :class:`~dmr.parsers.Parser` instance
if there's a :class:`~dmr.components.Body`
or :class:`~dmr.components.FileMetadata` components to parse.
Otherwise, for performance reasons, no parser is selected at all.
Nothing to parse - no parser is selected.

Here's how we select a parser, when it is needed:

1. We look at the ``Content-Type`` header
2. If it is not provided, we take the default parser,
   which is the first specified parser for the endpoint,
   aka the most specific one
3. If there's a ``Content-Type`` header,
   we try to exactly match known parsers based on their
   :attr:`~dmr.parsers.Parser.content_type` attribute.
   This is a positive path optimization
4. If there's no direct match, we now include parsers
   that have ``*`` pattern in supported content types.
   We match them in order based on ``'specificity', 'quality'``,
   the first match wins
5. If no parser fits the request's content type, we raise
   :exc:`~dmr.exceptions.RequestSerializationError`

We select :class:`~dmr.renderers.Renderer` instance
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
   :exc:`~dmr.exceptions.ResponseSchemaError`

.. note::

  When constructing responses manually, like:

  .. code-block:: python

    >>> from django.http import HttpResponse
    >>> response = HttpResponse(b'[]')

  The renderer is selected as usual, but no actual rendering is done.
  However, all other validation works as expected. Which means that even though
  renderer is not actually used, its metadata is still required
  to validate the response content type.

  But, when using :meth:`~dmr.controller.Controller.to_response`
  method, renderer will be executed.
  So, it is a preferred method for regular responses.

.. important::

  Settings always must have one parser
  and one renderer defined at all times,
  because utils like :func:`dmr.response.build_response`
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
:attr:`dmr.endpoint.Endpoint.request_negotiator_cls`
and :attr:`dmr.endpoint.Endpoint.response_negotiator_cls`
to completely change the negotiation logic to fit your needs.

This is possible on per-controller level.


Writing custom parsers and renderers
------------------------------------

And here's how our test ``xml`` parser and renderer are defined:

.. literalinclude:: /examples/negotiation/negotiation.py
   :caption: negotiation.py
   :language: python
   :linenos:

.. warning::

  This parser is only used as a demo, do not use it in production,
  prefer more tested and battle-proven solutions.


Using different schemes for different content types
---------------------------------------------------

Sometimes we have to accept different schemes based on the content type.
`According to the OpenAPI spec <https://swagger.io/docs/specification/v3_0/describing-request-body/describing-request-body/#requestbody-content-and-media-types>`_,
:class:`~dmr.components.Body`
should support different content types.

We utilize :data:`typing.Annotated`
and :func:`dmr.negotiation.conditional_type`:

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


.. _error-model-negotiation:

Using different error models for different content types
--------------------------------------------------------

The same can be done with error models.
Let's say you want to present JSON and XML error models differently.

We utilize the same technique :data:`typing.Annotated`
and :func:`dmr.negotiation.conditional_type`:

.. literalinclude:: /examples/negotiation/conditional_error_model.py
   :caption: views.py
   :language: python
   :linenos:

Note that you would also have to customize
:meth:`~dmr.controller.Blueprint.format_error`
accordingly.


Negotiation API
---------------

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
