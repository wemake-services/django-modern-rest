Header parameters
=================

You can define ``Headers`` parameters
the same way you define :class:`~dmr.components.Query`,
:class:`~dmr.components.Path` and
:class:`~dmr.components.Cookies` parameters.

.. note::

  Parsed ``Headers`` are available as ``self.parsed_headers``.

Since most headers uses ``-`` to separate words, but a variable
like ``cache-controll`` is not a valid variable name in Python.
So, you would have to use aliases for field names.
Remember, that headers are also case insensitive:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/components/headers_msgspec.py
        :caption: views.py
        :language: python
        :linenos:

    .. tab:: pydantic

      .. literalinclude:: /examples/components/headers_pydantic.py
        :caption: views.py
        :language: python
        :linenos:

What happens in this example?

1. We define a ``Headers`` model using :class:`msgspec.Struct`
   or :class:`pydantic.BaseModel`. Other types are also supported:
   :class:`typing.TypedDict`, :func:`dataclasses.dataclass`, etc
2. Next, we use :class:`~dmr.components.Headers` component,
   provide the model as a type parameter,
   and subclass it when defining :class:`~dmr.controller.Controller` type
3. Then we use ``self.parsed_headers`` that will have the correct model type


Duplicated headers
------------------

By default Django joins several headers into a single value.
This is a limitation of a WSGI protocol.
But, even ASGI workers are forced to do the same in Django for compatibility.

.. code::

  X-Tag: a
  X-Tag: b

Would become:

.. code:: python

  {'X-Tag': 'a,b'}

To force ``X-Tag`` to be a list you can use ``__dmr_split_commas__``.
Specify lower-case header field aliases
which needs to be split by a ``','`` char:

.. literalinclude:: /examples/components/headers_split.py
  :caption: views.py
  :language: python
  :linenos:

We don't inference ``__dmr_split_commas__`` value in any way,
it is up to users to set.

.. danger::

  Some headers like

  .. code::

    Accept: text/html, application/json
    Cache-Control: no-cache, no-store

  can naturally contain values with the ``','`` char.
  If you split them, you might get a messed up value.


Customizing OpenAPI metadata for Headers
----------------------------------------

See :ref:`customizing_parameter_openapi`.


API Reference
-------------

.. autoclass:: dmr.components.Headers
  :members:
  :show-inheritance:
