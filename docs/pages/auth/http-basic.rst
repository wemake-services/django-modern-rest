HTTP Basic Auth
===============

Docs: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication

.. warning::

  HTTP Basic Auth is very insecure.
  It is better than nothing, but is enough enough for nearly all real use-cases.
  Please, condider using :doc:`jwt` instead.


Requiring auth
--------------

To work with HTTP Basic auth you would need to subclass either
:class:`~dmr.security.http.HttpBasicSyncAuth` or
:class:`~dmr.security.http.HttpBasicAsyncAuth`
and override its sync or async (respectively) ``authenticate`` method,
which will decide whether or not passed username and password are correct.

Here's how to do it:

.. literalinclude:: /examples/auth/http_basic/auth.py
  :caption: auth.py
  :linenos:
  :language: python

Let's say we defined a **horribly weak** set
of username and password: ``admin / pass``.
Let's check that the auth works:

.. literalinclude:: /examples/auth/http_basic/views.py
  :caption: views.py
  :linenos:
  :language: python

Any other authentication method will be better then the one above.
Consider using :doc:`jwt` instead.


API Reference
-------------

.. autoclass:: dmr.security.http.HttpBasicSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.http.HttpBasicAsyncAuth
  :members:
  :inherited-members:

.. autofunction:: dmr.security.http.basic_auth
