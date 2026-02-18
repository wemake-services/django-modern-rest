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

We use :class:`dmr.serializer.SerializerContext` type
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
   :attr:`~dmr.serializer.SerializerContext.strict_validation`
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

TODO
