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

        from django_modern_rest.plugins.msgspec import MsgspecSerializer

    .. tab:: pydantic

      .. code:: python

        from django_modern_rest.plugins.pydantic import PydanticSerializer
