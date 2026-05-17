Returning files
===============

We support file and other binary responses.

.. warning::

  Returning files via Python and Django in particular
  is very performance inefficient.
  It should not be used for anything serious.

  Instead return files with S3-like systems or at least on a proxy-server level.

To do so, you indicate that you will return a file with
:class:`dmr.files.FileResponseSpec` and specify a file renderer.
We provide :class:`dmr.renderers.FileRenderer` for this case.

By default, ``FileResponseSpec()`` describes an inline file response.
It matches Django's ``FileResponse`` default behavior:

.. literalinclude:: /examples/using_controller/inline_file_response.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 13-14

Set ``as_attachment=True`` when Django's
:class:`django.http.FileResponse` is returned as an attachment. In this mode
`Content-Disposition <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition>`_
is always set and usually contains the filename sent to the client:

.. literalinclude:: /examples/using_controller/file_response.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 16-17, 22-23

The difference comes from the ``Content-Disposition`` HTTP header:
it tells clients whether the response body is expected to be displayed inline
or downloaded as an attachment.


API Reference
-------------

.. autoclass:: dmr.files.FileBody
  :members:

.. autoclass:: dmr.files.FileResponseSpec
  :members:

.. autofunction:: dmr.files.file_response_headers
