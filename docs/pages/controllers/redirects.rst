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

.. warning::

  :class:`~dmr.response.RedirectTo` accepts absolute and protocol-relative
  URLs, such as ``https://example.com/path`` and ``//example.com/path``.
  It validates the URL length and scheme, but does not check whether the
  destination host is trusted.
  Do not pass user-provided redirect targets to it without validation,
  because this can create an open redirect vulnerability.

  Use Django's
  `url_has_allowed_host_and_scheme <https://github.com/django/django/blob/73cc09f14f13fedddc14d6ba5b287cb33c24e4a4/django/utils/http.py#L274>`_
  helper to check untrusted redirect targets against the expected hosts
  and protocol:

  .. literalinclude:: /examples/using_controller/redirect_safe.py
    :caption: views.py
    :language: python
    :linenos:


API Reference
-------------

.. autoexception:: dmr.response.RedirectTo
  :members:
