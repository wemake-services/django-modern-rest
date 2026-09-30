Request body
============

The body can be anything: JSON, XML,
``application/x-www-form-urlencoded``,
or ``multipart/form-data``.

It depends on the :class:`~dmr.parsers.Parser`
that is being used for the endpoint.

.. note::

  The parsed ``Body`` parameter must be named ``parsed_body``.


Parsing JSON
------------

Here's how you can parse ``Body`` with a model:


.. tabs::

  .. tab:: msgspec

    We support :class:`msgspec.Struct`
    via :class:`~dmr.plugins.msgspec.MsgspecSerializer`.

    .. literalinclude:: /examples/components/body_msgspec.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: pydantic

    We support :class:`pydantic.BaseModel`
    via :class:`~dmr.plugins.pydantic.PydanticSerializer`.

    .. literalinclude:: /examples/components/body_pydantic.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: attrs

    We support :func:`attrs.define`
    via :class:`~dmr.plugins.msgspec.MsgspecSerializer`.

    .. literalinclude:: /examples/components/body_attrs.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: dataclasses

    We support :func:`dataclasses.dataclass` via both
    :class:`~dmr.plugins.msgspec.MsgspecSerializer`
    and :class:`~dmr.plugins.pydantic.PydanticSerializer`.

    .. literalinclude:: /examples/components/body_dataclasses.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: TypedDict

    We support :class:`typing.TypedDict` via both
    :class:`~dmr.plugins.msgspec.MsgspecSerializer`
    and :class:`~dmr.plugins.pydantic.PydanticSerializer`.

    .. literalinclude:: /examples/components/body_typed_dict.py
      :caption: views.py
      :language: python
      :linenos:

What happens in this example?

1. We define a ``Body`` model using :class:`msgspec.Struct`,
   :class:`pydantic.BaseModel`,
   :func:`attrs.define`,
   :class:`typing.TypedDict`, or :func:`dataclasses.dataclass`.
   Basically, the model definition is only limited
   by the :class:`~dmr.serializer.BaseSerializer` support
2. Next, we use the :data:`~dmr.components.Body` component,
   provide the model as a type parameter,
   and subclass it when defining the :class:`~dmr.controller.Controller` type
3. Then we use ``self.parsed_body`` which will have the correct model type


Parsing MsgPack
---------------

.. note::

  This feature requires ``'django-modern-rest[msgpack]'`` to be installed.

MsgPack is a binary, compact and really fast format for modern APIs.
Docs: https://msgpack.org

Bodies can be parsed using different :class:`dmr.parsers.Parser` types.
See our :doc:`../negotiation` guide on more information
about content negotiation.

Here's how ``msgpack`` will represent ``{"username": "example", "age": 22}``
(since it is a binary format, it will show some random unicode symbols:

- `examples/components/body.msgpack <https://github.com/wemake-services/django-modern-rest/blob/master/docs/examples/components/body.msgpack>`_
- `examples/components/body_wrong.msgpack <https://github.com/wemake-services/django-modern-rest/blob/master/docs/examples/components/body_wrong.msgpack>`_

The only visible difference from parsing JSON is specifying a different
:attr:`~dmr.controller.Controller.parsers` instance.

.. literalinclude:: /examples/components/body_msgpack.py
  :caption: views.py
  :language: python
  :linenos:


Optional body
-------------

Request body can have a default value, in this case it is optional:

.. tabs::

  .. tab:: msgspec

    .. literalinclude:: /examples/components/body_default_msgspec.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: pydantic

    .. literalinclude:: /examples/components/body_default_pydantic.py
      :caption: views.py
      :language: python
      :linenos:

Requests without a body get ``parsed_body=None``,
such bodies are documented with ``required: false`` in the OpenAPI schema.
Requests with a body are always validated, even when there's a default.

See :ref:`component-defaults` to learn more.


.. _fast-body-component:

Fast body parsing
-----------------

.. tip::

  ``BodyFast`` is generally x1.5 faster than ``Body``.

By default, ``Body`` is parsed in two steps:

1. The :class:`~dmr.parsers.Parser` decodes the raw request bytes
   into simple python objects, like :class:`dict` and :class:`list`,
   using no exact shape
2. Then, all components of the request (body, headers, query, etc)
   are validated together in a single call with the model that
   the :class:`~dmr.serializer.BaseSerializer` builds for the whole request,
   see :ref:`serializer-context`

This is flexible, but the intermediate python objects cost time.
But, we can add the shape in advance.
:data:`~dmr.components.BodyFast` does exactly that: it decodes
the request body directly into its model.
It is a drop-in replacement for ``Body``:

.. tabs::

  .. tab:: msgspec

    .. literalinclude:: /examples/components/body_fast_msgspec.py
      :caption: views.py
      :language: python
      :linenos:
      :emphasize-lines: 13

  .. tab:: pydantic

    .. literalinclude:: /examples/components/body_fast_pydantic.py
      :caption: views.py
      :language: python
      :linenos:
      :emphasize-lines: 13

What is different from ``Body``?

- The body is validated on its own, before all other components
  are validated together. When the body is invalid, other components
  are not validated at all: the error response only contains
  body errors, even if ``parsed_headers`` or ``parsed_query``
  are also invalid
- Error locations change: the body is validated as the root object,
  not as a part of the whole request, so the ``parsed_body`` prefix
  is gone. ``Body`` reports ``$.parsed_body.age`` for ``msgspec``
  and ``["parsed_body", "age"]`` for ``pydantic``,
  ``BodyFast`` reports ``$.age`` and ``["age"]`` for the same error.
  Top level errors have no location at all
- Invalid bytes, like malformed ``json``, are still reported
  as parsing errors, exactly like for ``Body``
- Strictness of ``msgspec`` decoding is controlled by
  :attr:`~dmr.plugins.msgspec.MsgspecJsonParser.strict`
  and :attr:`~dmr.plugins.msgspec.MsgpackParser.strict` attributes,
  which are lax by default, just like the regular request validation.
  :attr:`~dmr.endpoint.SerializerContext.strict_validation` has no effect
  on fast bodies

.. tip::

  ``BodyFast`` works best if there are no other components.

Everything else works the same: :ref:`defaults <component-defaults>`,
:ref:`conditional types <conditional-types>`, OpenAPI schema generation,
and :doc:`response validation <../validation>`.

.. note::

  Not all combinations of serializers and parsers really support ``BodyFast``.
  :class:`~dmr.plugins.msgspec.MsgspecJsonParser`,
  :class:`~dmr.plugins.msgspec.MsgpackParser`, and
  :class:`~dmr.plugins.pydantic.PydanticFastSerializer`
  do support this mode. Other parsers, like :class:`~dmr.parsers.JsonParser`,
  ignore the model and work the default way: the body is validated
  together with all other components, exactly like with ``Body``,
  including the ``parsed_body`` prefix in error locations.
  There's no speedup in this case, but nothing breaks either.

  :class:`~dmr.plugins.pydantic.PydanticSerializer` does not support
  ``BodyFast`` at all. Because it is actually slower
  to do in all measured cases.
  Serializers check that in :meth:`~dmr.serializer.BaseSerializer.validate`
  during the import time, so you won't be able to create an unsupported case.


Customizing the OpenAPI metadata for Body
-----------------------------------------

See :ref:`customizing_body_openapi`.


Parsing forms
-------------

.. note::

  We don't recommend using forms. If you can avoid using this feature
  and switch to JSON, you totally should.

  Forms are only needed for compatibility with older APIs, strange libraries,
  or existing workflows.

Here's an example how one can send ``application/x-www-form-urlencoded``
form data to an API endpoint with the help
of :class:`~dmr.parsers.FormUrlEncodedParser`:

.. literalinclude:: /examples/components/body_form.py
  :caption: views.py
  :language: python
  :linenos:

.. tip::

  If you are using Django 6.1+ and have a lot of form requests,
  you can swap the :attr:`django.http.HttpRequest.multipart_parser_class`
  attribute of request objects for faster parsing. We recommend using
  the `multipart <https://github.com/defnull/multipart>`_ package for that.
  It works twice as fast.


Forcing lists and casting nulls in forms
----------------------------------------

.. warning::

  All of the features below only work for
  ``application/x-www-form-urlencoded`` and ``multipart/form-data``
  parsers. JSON and other "modern" formats are not affected.

Django's form parsing algorithm is 20+ years old
at the moment of writing this doc.

There are some known quirks to it.

Forcing lists
~~~~~~~~~~~~~

Django uses :class:`django.utils.datastructures.MultiValueDict`
to store body data when parsing forms. Due to its API,
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

  We split all data by ``','``. If your data contains ``','`` as a regular
  value, it might be corrupted.

  Be careful when you use this with fields which do not contain ``','``,
  like list of ints, UUIDs, or slugs.

Casting nulls
~~~~~~~~~~~~~

It is hard to pass ``None`` as a value in a form.
To solve the need for ``None``, many places offer to pass ``'null'`` as a string.
We can cast ``'null'`` back to ``None`` if ``__dmr_cast_null__`` is specified.

.. literalinclude:: /examples/components/body_cast_null.py
  :caption: views.py
  :language: python
  :linenos:

You can combine this feature with
both ``__dmr_split_commas__`` and ``__dmr_force_list__`` as well.


Conditional models
------------------

``django-modern-rest`` supports using different request models
for different request content types.

See :ref:`conditional-types` to learn more.


API Reference
-------------

.. autodata:: dmr.components.Body

.. autodata:: dmr.components.BodyFast

.. autoclass:: dmr.components.BodyComponent
  :members:
  :show-inheritance:
