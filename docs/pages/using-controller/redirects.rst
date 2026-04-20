Returning redirects
===================

We support returning redirects from API endpoints with
:class:`~dmr.response.RedirectTo` exception with :func:`~dmr.endpoint.modify`:

.. literalinclude:: /examples/using_controller/redirect_error.py
  :caption: views.py
  :language: python
  :linenos:

We model ``RedirectTo`` as an exception, because you are not allowed
to return :class:`~django.http.HttpResponse` objects
from :func:`~dmr.endpoint.modify` endpoints.

.. note::

  :class:`~dmr.response.APIError` does not support ``3xx`` status codes.
  Redirects are different from regular errors.

The second way is to use
default Django's :class:`django.http.HttpResponseRedirect`
together with :func:`~dmr.endpoint.validate`:

.. literalinclude:: /examples/using_controller/redirect_response.py
  :caption: views.py
  :language: python
  :linenos:

Note that in both cases you would need to document ``Location`` header
in a response spec.


API Reference
-------------

.. autoexception:: dmr.response.RedirectTo
  :members:
