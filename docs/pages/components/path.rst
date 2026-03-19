Path parameters
===============

Using native Django path params
-------------------------------

You don't have to use :class:`~dmr.components.Path` to parse url parameters.
By default Django puts all url parameters
into ``self.args`` and ``self.kwargs``.

Let's take a look at the full example:

.. literalinclude:: /examples/components/path_raw.py
  :caption: views.py
  :language: python
  :linenos:

What happens here?

1. We define a controller that uses regular ``self.kwargs``
   dict with path params with no extra parsing from our side
2. We define a custom :class:`~dmr.metadata.ResponseSpec`
   instance with ``404`` as a response code,
   :class:`~dmr.components.Path` injects this response automatically,
   but since we don't use – we have to do that manually
   for our :ref:`response_validation` to work
3. We also show how one can use :class:`~dmr.response.APIError`
   to raise custom ``404`` errors when some objects are not found
4. We define an api url with :func:`django.urls.path`
   (or with :func:`django.urls.re_path`)
   and a common Django syntax for path parameters:
   ``'user/<int:user_id>/post/<uuid:post_id/'``

Django supports multiple pre-defined path converter types:
``int``, ``uuid``, ``str``, ``slug``, ``path``.

.. seealso::

  - https://docs.djangoproject.com/en/6.0/topics/http/urls/
  - https://docs.djangoproject.com/en/6.0/ref/urlresolvers/

The main downside of this method is that ``self.kwargs`` is typed
as ``dict[str, Any]``. Which is not always ideal.
If you need typed path parameters,
use :class:`~dmr.components.Path` component with a model.

.. note::

  If you are using custom url convereters
  and :func:`django.urls.register_converter`,
  we won't know your url parameter schema type in advance.
  We default to ``str`` type for all url converters.

  However, if you are using a different converter schema type,
  you can use set ``__dmr_converter_schema__`` attribute
  with the specific type that you need in the schema.


Using Path component and parsing models
---------------------------------------

When do you need to parse path parameters into models?

1. When you need typed path parameter model
2. When they have more metadata then regular Django can provide.
   For example: only positive integers. Or ``str`` with an exact length
3. When you only need ``self.kwargs`` to be parsed,
   because ``Path`` does not support variadic url args from ``self.args``

You can define ``Path`` parameters
the same way you define :class:`~dmr.components.Headers`,
:class:`~dmr.components.Query` and
:class:`~dmr.components.Cookies` parameters.

.. note::

  Parsed ``Path`` is available as ``self.parsed_path``.

This is how you can parse ``Path`` parameters into a model:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/components/path_msgspec.py
        :caption: views.py
        :language: python
        :linenos:

    .. tab:: pydantic

      .. literalinclude:: /examples/components/path_pydantic.py
        :caption: views.py
        :language: python
        :linenos:

What happens in this example?

1. We define a ``Path`` model using :class:`msgspec.Struct`
   or :class:`pydantic.BaseModel`. Other types are also supported:
   :class:`typing.TypedDict`, :func:`dataclasses.dataclass`, etc
2. Next, we use :class:`~dmr.components.Path` component,
   provide the model as a type parameter,
   and subclass it when defining :class:`~dmr.controller.Controller` type
3. Then we use ``self.parsed_path`` that will have the correct model type

What is the difference from the raw ``path()`` model?

1. ``Path`` component automatically injects ``404`` error into the final schema
2. It performs a second validation of the ``self.kwargs``
   with new extra metadata from the ``Path`` model
3. It add ``self.parsed_path`` attribute

.. important::

  Make sure that your ``path()`` URL pattern and ``Path`` model fields match.
  We don't automatically validate it.


Customizing OpenAPI metadata for Path
-------------------------------------

See :ref:`customizing_parameter_openapi`.


API Reference
-------------

.. autoclass:: dmr.components.Path
  :members:
  :show-inheritance:
