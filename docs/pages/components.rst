Components
==========

``django-modern-rest`` utilizes component approach to parse all
the unstructured things like headers, body, and cookies
into a string typed and validated model.

To use a component, you can just add it as a base class to your
:class:`~dmr.controller.Controller`
or :class:`~dmr.controller.Blueprint`.

How does it work?

- When controller / blueprint is first created,
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


Existing components
-------------------

Parsing headers
~~~~~~~~~~~~~~~

.. autoclass:: dmr.components.Headers

Parsing query string
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.components.Query

Parsing request body
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.components.Body

Body can be anything: json, xml,
``application/x-www-form-urlencoded``, or ``multipart/form-data``.

It depends on the :class:`~dmr.parsers.Parser`
that is being used for the endpoint.

Here's an example how one can send ``application/x-www-form-urlencoded``
form data to an API endpoint with the help
of :class:`~dmr.parsers.FormUrlEncodedParser`:

.. literalinclude:: /examples/components/form_body.py
  :caption: views.py
  :language: python
  :linenos:

Parsing path parameters
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.components.Path

Parsing cookies
~~~~~~~~~~~~~~~

.. autoclass:: dmr.components.Cookies

Parsing files
~~~~~~~~~~~~~

There are several way of how users can send files to a REST API:

1. Via ``multipart/form-data`` requests.
   It supports passing multiple files at once,
   it also supports sending other body parameters together with the files.
   It is the best option for 95% of cases. This way requires our
   :class:`~dmr.parsers.MultiPartParser` to be used
2. Via direct requests with a single file and a concrete content-type metadata
3. Via base64 encoded strings inside a json / xml files.
   Is only suitable for really small files

We support all three options.
The first option is officially supported.
The second option is not supported yet, but can be, even by user-code only.
While the third way has no specific support,
but is possible to be implemented by users directly.

.. autoclass:: dmr.components.FileMetadata


.. rubric:: Sending files with extra body parameters

It might be required to send some files as ``multipart/form-data``
together with some extra information, like ``user_id``.

This is also supported:

.. literalinclude:: /examples/components/files_with_body.py
  :caption: views.py
  :language: python
  :linenos:

.. rubric:: Sending files with json as a body parameter

You can send complex data together with files as ``multipart/form-data``.
To do so, you would need to encode json as a string
and attach it to a form data field.

.. literalinclude:: /examples/components/files_with_json_body.py
  :caption: views.py
  :language: python
  :linenos:


API Reference
-------------

.. autoclass:: dmr.components.ComponentParser
   :members:
