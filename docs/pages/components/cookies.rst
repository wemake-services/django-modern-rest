Cookie parameters
=================

You can define ``Cookies`` parameters
the same way you define :data:`~dmr.components.Headers`,
:data:`~dmr.components.Path` and
:data:`~dmr.components.Query` parameters.

.. note::

  Parsed ``Cookie`` parameter must be named ``parsed_cookies``.

This is how you can parse ``Cookies`` parameters:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/components/cookies_msgspec.py
        :caption: views.py
        :language: python
        :linenos:

    .. tab:: pydantic

      .. literalinclude:: /examples/components/cookies_pydantic.py
        :caption: views.py
        :language: python
        :linenos:

What happens in this example?

1. We define a ``Cookies`` model using :class:`msgspec.Struct`
   or :class:`pydantic.BaseModel`. Other types are also supported:
   :class:`typing.TypedDict`, :func:`dataclasses.dataclass`, etc
2. Next, we use :data:`~dmr.components.Cookies` component,
   provide the model as a type parameter,
   and subclass it when defining :class:`~dmr.controller.Controller` type
3. Then we use ``self.parsed_cookies`` that will have the correct model type

Cookies are case-sensitive.


Customizing OpenAPI metadata for Cookies
----------------------------------------

See :ref:`customizing_parameter_openapi`.


API Reference
-------------

.. autodata:: dmr.components.Cookies

.. autoclass:: dmr.components.CookiesComponent
  :members:
  :show-inheritance:
