Plugins
=======

To be able to support multiple :term:`serializer` models
like ``pydantic`` and ``msgspec``, we have a concept of a plugin.

There are several bundled ones, but you can write your own as well.
To do that see our advanced :ref:`serializer` guide.

As a user you are only interested in choosing the right plugin
for the :term:`controller` definition.

.. tabs::

  .. tab:: msgspec

    .. code:: python

      from dmr.plugins.msgspec import MsgspecSerializer

  .. tab:: pydantic

    .. tip::

      If you only use ``json`` :doc:`parsers and renderers <negotiation>`,
      it would be faster to use
      :class:`~dmr.plugins.pydantic.PydanticFastSerializer` instead.

    .. code:: python

      from dmr.plugins.pydantic import PydanticSerializer


Customizing serializers
-----------------------

There are several things why you can possibly want
to customize an existing serializer.

Support more data types
~~~~~~~~~~~~~~~~~~~~~~~

By default,
:meth:`~dmr.serializer.BaseSerializer.serialize_hook`
and
:meth:`~dmr.serializer.BaseSerializer.deserialize_hook`
support not that many types.

You can customize the serializer to know how to serializer / deserialize
more types by extending it and customizing the method you need.


Customizing the serializer context
----------------------------------

We use :class:`dmr.endpoint.SerializerContext` type
to deserialize all components from a single model, so it would be much faster
than parsing each component separately.

This class can be customized for several reasons.

Change the default strictness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tools like ``pydantic`` offer several useful type conversions in non-strict mode.
For example, ``'1'`` can be parsed as ``1`` if strict mode is not enabled.

It is kinda useful for request bodies, where you don't control the clients.

Here's how we determine the default strictness for ``pydantic`` models:

1. If
   :attr:`~dmr.endpoint.SerializerContext.strict_validation`
   is not ``None``, we return the serializer-level strictness
2. Then ``pydantic`` looks at ``strict`` attribute
   in :class:`~pydantic.config.ConfigDict`
3. Then ``pydantic`` looks at ``strict`` attribute
   for individual :func:`~pydantic.fields.Field` items

We recommend to change the strictness on a per-model basis, but if you want to,
you can subclass the ``SerializerContext`` to be strict / non-strict
and use it for all controllers.


Endpoint optimizers
-------------------

Before actually serving any requests, during import-time,
we try to optimize the future validation.

For example, :class:`pydantic.TypeAdapter` takes time to be created.
Why doing it on the first request, when we can do that during the import time?

Each serializer must provide a type, which must be a subclass
of :class:`~dmr.serializer.BaseEndpointOptimizer`
to optimize / pre-compile / create / cache things that it can.


Writing a custom plugin
------------------------

Our API is flexible enough to potentially support any custom
third-party serializers of your choice, like:

- https://github.com/python-attrs/cattrs
- https://github.com/reagento/adaptix
- etc

Follow the API of :class:`~dmr.plugins.pydantic.PydanticSerializer`
and :class:`~dmr.plugins.msgspec.MsgspecSerializer`.

You would need to:

- Provide a way to serializer and deserialize your models
- Provide serializer error converter by overriding
  :meth:`~dmr.serializer.BaseSerializer.serialize_validation_error` method
- Provide a way to get the OpenAPI / JsonSchema schema from your models,
  see :class:`dmr.serializer.BaseSchemaGenerator`. Example implementations:
  :class:`~dmr.plugins.pydantic.schema.PydanticSchemaGenerator`
  and :class:`~dmr.plugins.msgspec.schema.MsgspecSchemaGenerator`


Pydantic plugin
---------------

PydanticFastSerializer
~~~~~~~~~~~~~~~~~~~~~~

``pydantic`` plugin contains one extra serializer optimized for ``json`` usage.
Our regular API requires :doc:`parsers and renderers <negotiation>`
to format the final response,
so you can negotiate the request and response formats.

However, for cases when you only have ``json`` requests
and responses (which is quite common), use
:class:`~dmr.plugins.pydantic.PydanticFastSerializer`.

.. warning::

  It will ignore all parsers and serializers and use the ``pydantic``
  own way to serialize and deserialize objects to ``json`` bytestring.

It will work from **3 up 10 times** faster depending on the data
then the common serializer.

.. literalinclude:: /examples/plugins/pydantic_fast.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 12

No API changes are required to use it
if you don't use other request / response formats.

Serialization / deserialization flags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We have to special attributes to change how ``pydantic`` serializes data:

1. :attr:`~dmr.plugins.pydantic.PydanticSerializer.to_json_kwargs`
   for serialization purposes
2. :attr:`~dmr.plugins.pydantic.PydanticSerializer.to_model_kwargs`
   for deserialization purposes

By default these flags only pass ``{'by_alias': True}``
to support field aliases, when they are defined.

For example, when working with :class:`pydantic.types.Json`,
one can set ``round_trip`` to ``True``
(which is not passed by default,
because it disables :func:`computed fields <pydantic.fields.computed_field>`):

.. literalinclude:: /examples/plugins/pydantic_round_trip.py
  :caption: views.py
  :language: python
  :linenos:

.. seealso::

  Docs: https://docs.pydantic.dev/2.3/usage/types/json/


Msgspec plugin
--------------

attrs support
~~~~~~~~~~~~~

We support :func:`attrs.define` via ``msgspec`` compatibility layer.
It has its own limitations.
See `msgspec docs <https://jcristharif.com/msgspec/supported-types.html#attrs>`_.

Native support of ``attrs`` can be implemented in the future
with its own serializer.
