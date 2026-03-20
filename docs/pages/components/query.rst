Query parameters
================

You can define ``Query`` parameters
the same way you define :class:`~dmr.components.Headers`,
:class:`~dmr.components.Path` and
:class:`~dmr.components.Cookies` parameters.

.. note::

  Parsed ``Query`` is available as ``self.parsed_query``.

This is how you can parse ``Query`` parameters:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/components/query_msgspec.py
        :caption: views.py
        :language: python
        :linenos:

    .. tab:: pydantic

      .. literalinclude:: /examples/components/query_pydantic.py
        :caption: views.py
        :language: python
        :linenos:

What happens in this example?

1. We define a ``Query`` model using :class:`msgspec.Struct`
   or :class:`pydantic.BaseModel`. Other types are also supported:
   :class:`typing.TypedDict`, :func:`dataclasses.dataclass`, etc
2. Next, we use :class:`~dmr.components.Query` component,
   provide the model as a type parameter,
   and subclass it when defining :class:`~dmr.controller.Controller` type
3. Then we use ``self.parsed_query`` that will have the correct model type


Customizing OpenAPI metadata for Query
--------------------------------------

See :ref:`customizing_parameter_openapi`.


Forcing query params to be a list
---------------------------------

Internally query parameters are represented
as :class:`django.utils.datastructures.MultiValueDict` in Django.
It supports setting and getting several values for a single key.

Users can customize how they want their values:
as single values or as lists of values.
To do so, use ``__dmr_force_list__`` optional attribute.
Set it to :class:`frozenset` of field aliases that need to be lists.
All other values will be regular single values:

.. literalinclude:: /examples/components/query_list.py
  :caption: views.py
  :language: python
  :linenos:

We don't inference ``__dmr_force_list__`` value in any way,
it is up to users to set.


Casting nulls
-------------

Queries in Django cannot be ``None`` by default.
So, when some tools send ``'null'`` as a way to represent ``None``,
we need to handle that.

To do so, set the field aliases that should do
that into ``__dmr_cast_null__``:

.. literalinclude:: /examples/components/query_cast.py
  :caption: views.py
  :language: python
  :linenos:

We don't inference ``__dmr_cast_null__`` value in any way,
it is up to users to set.


API Reference
-------------

.. autoclass:: dmr.components.Query
  :members:
  :show-inheritance:
