Authentication
==============

Disabling auth
--------------

TODO


General API Reference
---------------------

.. autoclass:: django_modern_rest.security.SyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.AsyncAuth
  :members:
  :inherited-members:


Django session auth API
-----------------------

.. autoclass:: django_modern_rest.security.DjangoSessionSyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.DjangoSessionAsyncAuth
  :members:
  :inherited-members:


HTTP Basic Auth API
-------------------

.. autoclass:: django_modern_rest.security.http.HttpBasicSyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.http.HttpBasicAsyncAuth
  :members:
  :inherited-members:

.. autofunction:: django_modern_rest.security.http.basic_auth


JWT API
-------

.. important::

  To use ``jwt`` you must install ``django-modern-rest[jwt]`` extra.


.. autoclass:: django_modern_rest.security.jwt.JWTToken
  :members:

.. autoclass:: django_modern_rest.security.jwt.JWTSyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.jwt.JWTAsyncAuth
  :members:
  :inherited-members:
