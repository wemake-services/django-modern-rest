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
