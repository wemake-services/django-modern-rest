HTTP Basic Auth
===============

Docs: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication

.. warning::

  HTTP Basic Auth is very insecure.
  It is better than nothing, but is enough enough for nearly all real use-cases.
  Please, condider using :doc:`jwt` instead.

TODO

API Reference
-------------

.. autoclass:: django_modern_rest.security.http.HttpBasicSyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.http.HttpBasicAsyncAuth
  :members:
  :inherited-members:

.. autofunction:: django_modern_rest.security.http.basic_auth
