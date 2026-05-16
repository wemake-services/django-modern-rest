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
It can also accept a specific ``content_type`` to render.
Set ``as_attachment=True`` when Django's ``FileResponse`` is returned as
an attachment:

.. literalinclude:: /examples/using_controller/file_response.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 16, 17

If you don't pass ``filename`` or ``as_attachment=True`` to Django's
``FileResponse``, use the default ``FileResponseSpec()``. It will be returned
inline and ``Content-Disposition`` won't be required:

.. literalinclude:: /examples/using_controller/inline_file_response.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 12, 13


API Reference
-------------

.. autoclass:: dmr.files.FileBody
  :members:

.. autoclass:: dmr.files.FileResponseSpec
  :members:
