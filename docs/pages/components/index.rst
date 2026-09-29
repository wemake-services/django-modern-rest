Components
==========

``django-modern-rest`` utilizes component approach to parse all
the unstructured things like headers, body, and cookies
into a strongly typed and validated model.

To use a component, you can just add it as a parameter
to your endpoint method inside a :class:`~dmr.controller.Controller`.

How does it work?

- In **import time**, when controller is first created,
  we iterate over all existing endpoints in this class
- For each endpoint we fetch method annotations and find all
  :class:`~dmr.components.ComponentParser` objects,
  they will be treated as component parsers
- Next, we create a request parsing model during the import time,
  with all combined fields to be parsed later
- In **runtime**, when request is received, we provide the needed data
  for this single parsing model
- If everything is ok, we call the needed endpoint with the correct data
- If there's a parsing error we raise
  :exc:`~dmr.exceptions.RequestSerializationError`
  and return a beautiful error message for the user

You can use existing ones or create your own.

.. note::

  All existing components should only be inherited for parsing.
  If you want to change the implementation details
  of a component – create a new one from scratch.

  You can still delegate parts of the work to existing ones.


What is inside a component?
---------------------------

All components consist of two parts:

1. The first one is a :class:`~dmr.components.ComponentParser` subclass,
   which knows how to provide the required data for itself, build OpenAPI
   schemas and etc. For example: :class:`~dmr.components.QueryComponent`
2. The second part is a :data:`typing.Annotated` based annotation that
   has a component parser instance as metadata.
   These annotations will be used by the end users.
   For example, :data:`~dmr.components.Query`

.. note::

  Type aliases have first-class support:
  ``UserBody: TypeAlias = Body[User]`` and ``type UserBody = Body[User]``
  both work as component annotations, including aliases of aliases
  and subscripted generic aliases like ``type Payload[ModelT] = Body[ModelT]``.


.. _component-defaults:

Default values
--------------

Component parameters can have default values, just like any other
Python parameters. When a request has no data for such a component,
the endpoint receives its default value.
Defaults are real Python defaults: they are passed as-is,
without any copies. Regular parameters with defaults,
like ``help_text: str = 'default'``, can be mixed with components.

.. tabs::

  .. tab:: msgspec

    .. literalinclude:: /examples/components/defaults_msgspec.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: pydantic

    .. literalinclude:: /examples/components/defaults_pydantic.py
      :caption: views.py
      :language: python
      :linenos:

What counts as "no data" for each component?

- :data:`~dmr.components.Body` has no data when the request body is empty,
  for ``multipart/form-data`` requests: when there are no fields and no files
- :data:`~dmr.components.Query` has no data when there are no query parameters
- :data:`~dmr.components.Headers` has no data when there are no headers,
  which is practically never the case for real requests
- :data:`~dmr.components.Cookies` has no data when there are no cookies
- :data:`~dmr.components.Path` has no data when the url pattern
  has no parameters
- :data:`~dmr.components.FileMetadata` has no data when no files were uploaded

Custom components receive the default value as the *default* parameter
of :meth:`~dmr.components.ComponentParser.provide_context_data`
and decide when to return it.

When the request has some data, it is always validated against the model,
so ``Body[Model | None] = None`` still returns an error
for invalid bodies, it does not silently fall back to ``None``.

.. note::

  Defaults are passed to the model that parses the whole request,
  so the rules of the serializer's model type apply:
  :func:`dataclasses.dataclass` for ``pydantic``
  and :class:`msgspec.Struct` for ``msgspec`` reject mutable defaults
  like ``[]`` and non-frozen model instances during the import time.
  Use ``None`` or frozen models as defaults.

.. warning::

  The ``| None`` part must be inside the component annotation,
  so it must be ``Body[Model | None] = None``
  and not ``Body[Model] | None = None``.

  The second form hides the component behind a union,
  so it would not be parsed at all.
  We raise :exc:`~dmr.exceptions.UnsolvableAnnotationsError`
  during the import time for any annotation that hides a component
  inside other types, like ``Body[Model] | None`` or ``list[Body[Model]]``.

Defaults are also reflected in the OpenAPI schema:
a :data:`~dmr.components.Body` with a default is documented
with ``required: false``, and parameters of other components
with defaults are documented as not required.
Path parameters are always required by the OpenAPI specification.


Browse components
-----------------

.. grid:: 3 3 2 2
    :class-row: surface
    :padding: 0
    :gutter: 2

    .. grid-item-card:: Query
      :link: query
      :link-type: doc

      Parsing query parameters.

    .. grid-item-card:: Headers
      :link: headers
      :link-type: doc

      Parsing header parameters.

    .. grid-item-card:: Cookies
      :link: cookies
      :link-type: doc

      Parsing cookie parameters.

    .. grid-item-card:: Path
      :link: path
      :link-type: doc

      Parsing path parameters.

    .. grid-item-card:: Body
      :link: body
      :link-type: doc

      Parsing request body.

    .. grid-item-card:: Files
      :link: files
      :link-type: doc

      Uploading files.


API Reference
-------------

.. autoclass:: dmr.components.ComponentParser
   :members:


.. toctree::
   :hidden:

   query.rst
   headers.rst
   cookies.rst
   path.rst
   body.rst
   files.rst
