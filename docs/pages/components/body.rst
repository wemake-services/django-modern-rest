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


Parsing forms
-------------

Here's an example how one can send ``application/x-www-form-urlencoded``
form data to an API endpoint with the help
of :class:`~dmr.parsers.FormUrlEncodedParser`:

.. literalinclude:: /examples/components/body_form.py
  :caption: views.py
  :language: python
  :linenos:


API Reference
-------------

.. autoclass:: dmr.components.Body
  :members:
  :show-inheritance:
