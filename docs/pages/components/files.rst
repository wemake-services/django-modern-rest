Uploading files
===============

There are several way of how users can send files to a REST API:

1. Via ``multipart/form-data`` requests.
   It supports passing multiple files at once,
   it also supports sending other body parameters together with the files.
   It is the best option for 95% of cases. This way requires our
   :class:`~dmr.parsers.MultiPartParser` to be used
2. Via direct requests with a single file and a concrete content-type metadata
3. Via base64 encoded strings inside a json / xml files.
   Is only suitable for really small files

Currently we support only the first option.
The second option is not supported yet, but can be in the future releases.
Currently users can implement their own :class:`~dmr.parsers.Parser` to do that.
While the third way has no specific support,
but is possible to be implemented by users directly.

.. danger::

  Uploading files with Python and Django can be really slow.
  For most cases it would be a better idea to use S3-like system
  to upload user-generated content.

  Sync uploads must not ever be used.
  Even very small amount of traffic will completely block your app.


Parsing files
-------------

.. note::

  Parsed ``FileMetadata`` is available as ``self.parsed_file_metadata``.
  While file objects themselves are available as ``self.request.FILES``.
  See :attr:`django.http.HttpRequest.FILES` for more info.

We don't provide any extra abstractions on top of Django's file uploads.

.. note::

  Official Django docs:
  https://docs.djangoproject.com/en/stable/topics/http/file-uploads/

All Django features for file uploads work as well for ``django-modern-rest``.
Like `FILE_UPLOAD_MAX_MEMORY_SIZE <https://docs.djangoproject.com/en/stable/ref/settings/#file-upload-max-memory-size>`_
or `FILE_UPLOAD_HANDLERS <https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-FILE_UPLOAD_HANDLERS>`_.

So, we do not touch Django's internal logic for file uploads.
What we do instead is: we provide extra metadata
to be validated / rendered in the schema:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/components/files_msgspec.py
        :caption: views.py
        :language: python
        :linenos:

    .. tab:: pydantic

      .. literalinclude:: /examples/components/files_pydantic.py
        :caption: views.py
        :language: python
        :linenos:

What happens in this example?

1. We define a ``FileMetadata`` model using :class:`msgspec.Struct`
   or :class:`pydantic.BaseModel`. Other types are also supported:
   :class:`typing.TypedDict`, :func:`dataclasses.dataclass`, etc
2. Next, we use :class:`~dmr.components.FileMetadata` component,
   provide the model as a type parameter,
   and subclass it when defining :class:`~dmr.controller.Controller` type
3. Then we use ``self.parsed_file_metadata``
   that will have the correct model type

.. note::

  Unlike raw Django, ``django-modern-rest`` allows file uploads
  for all HTTP methods with defined bodies.

Here's the list of fields that we support as a metadata:

.. code:: python

   [
      'size',
      'name',
      'content_type',
      'charset',
      'content_type_extra',
   ]

We don't copy content for the validation, only metadata.


Customizing OpenAPI metadata for FileMetadata
---------------------------------------------

See :ref:`customizing_body_openapi`.


Sending files with extra body parameters
----------------------------------------

It might be required to send some files as ``multipart/form-data``
together with some extra information, like ``user_id``.

This is also supported:

.. literalinclude:: /examples/components/files_with_body.py
  :caption: views.py
  :language: python
  :linenos:

To do that also define :class:`~dmr.components.Body` component
in the same controller.


Sending files with json as a body parameter
-------------------------------------------

You can send complex data together with files as ``multipart/form-data``.
To do so, you would need to encode json as a string
and attach it to a form data field.

.. literalinclude:: /examples/components/files_with_json_body.py
  :caption: views.py
  :language: python
  :linenos:

The easiest way to do this would be to declare
a field as ``pydantic.Json``.

However, this can be done with ``msgspec`` as well.


API Reference
-------------

.. autodata:: dmr.components.FileMetadata

.. autoclass:: dmr.components.FileMetadataComponent
  :members:
  :show-inheritance:
