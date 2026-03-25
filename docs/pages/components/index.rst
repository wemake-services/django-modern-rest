Components
==========

``django-modern-rest`` utilizes component approach to parse all
the unstructured things like headers, body, and cookies
into a string typed and validated model.

To use a component, you can just add it as a base class to your
:class:`~dmr.controller.Controller`.

How does it work?

- When controller is first created (in import time),
  we iterate over all existing components in this class
- Next, we create a request parsing model during the import time,
  with all combined fields to be parsed later
- In runtime, when request is received, we provide the needed data
  for this single parsing model
- If everything is ok, we call the needed endpoint with the correct data
- If there's a parsing error we raise
  :exc:`~dmr.exceptions.RequestSerializationError`
  and return a beautiful error message for the user

You can use existing ones or create our own.

.. note::

  All existing components should only be inherited for parsing.
  If you want to change the implementation details
  of a component – create a new one from scratch.

  You can still delegate parts of the work to existing ones.


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
