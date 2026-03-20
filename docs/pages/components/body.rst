Request body
============

Body can be anything: json, xml,
``application/x-www-form-urlencoded``,
or ``multipart/form-data``.

It depends on the :class:`~dmr.parsers.Parser`
that is being used for the endpoint.

.. note::

  Parsed ``Body`` is available as ``self.parsed_body``.


Parsing JSON
------------

Here's how you can parse ``Body`` with a model:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/components/body_msgspec.py
        :caption: views.py
        :language: python
        :linenos:

    .. tab:: pydantic

      .. literalinclude:: /examples/components/body_pydantic.py
        :caption: views.py
        :language: python
        :linenos:

What happens in this example?

1. We define a ``Body`` model using :class:`msgspec.Struct`
   or :class:`pydantic.BaseModel`. Other types are also supported:
   :class:`typing.TypedDict`, :func:`dataclasses.dataclass`
2. Next, we use :class:`~dmr.components.Body` component,
   provide the model as a type parameter,
   and subclass it when definiting :class:`~dmr.controller.Controller` type
3. Then we use ``self.parsed_body`` that will have the correct model type


Customizing OpenAPI metadata for Body
-------------------------------------

See :ref:`customizing_body_openapi`.


Parsing forms
-------------

.. note::

  We don't recommend using forms. If you can avoid using this feature
  and switch to json – you totally should.

  Forms are only needed for compatibility with older APIs, strange libs,
  existing workflows.

Here's an example how one can send ``application/x-www-form-urlencoded``
form data to an API endpoint with the help
of :class:`~dmr.parsers.FormUrlEncodedParser`:

.. literalinclude:: /examples/components/body_form.py
  :caption: views.py
  :language: python
  :linenos:


Forcing lists and casting nulls in forms
----------------------------------------

.. warning::

  All of the features below only work for
  ``application/x-www-form-urlencoded`` and ``multipart/form-data``
  parsers. Json and other "modern" formats are not affected.

Django's form parsing algorithm is 20+ years old
at the moment of writing this doc.

There are some known quirks to it.

Forcing lists
~~~~~~~~~~~~~

Django uses :class:`django.utils.datastructures.MultiValueDict`
to store body data, when parsing forms. Due to its API,
it does not give ``list`` objects back easily.
So, when we need a list for a field, we need to force it like this:

.. literalinclude:: /examples/components/body_force_list.py
  :caption: views.py
  :language: python
  :linenos:

Split commas
~~~~~~~~~~~~

Another problem that might happen is that some field might
look like ``{'foo': 'bar,baz'}``, not ``{'foo': ['bar', 'baz']}``.
To solve this, one can use a different magic attribute:

.. literalinclude:: /examples/components/body_split_commas.py
  :caption: views.py
  :language: python
  :linenos:

.. warning::

  We split all data by ``','``, if your data contains ``','`` as a regular
  value, it might be corrupted.

  Be careful to use this with fields which does not contain ``','``.
  Like list of ints, uuids, or slugs.

Casting nulls
~~~~~~~~~~~~~

It is hard to pass ``None`` as a value in a form.
To solve the need for ``None`` many places offer to pass ``'null'`` as a string.
We can cast ``'null'`` back to ``None`` if ``__dmr_cast_null__`` is specified.

.. literalinclude:: /examples/components/body_cast_null.py
  :caption: views.py
  :language: python
  :linenos:

You can combine this feature with
both ``__dmr_split_commas__`` and ``__dmr_force_list__`` as well.


API Reference
-------------

.. autoclass:: dmr.components.Body
  :members:
  :show-inheritance:
