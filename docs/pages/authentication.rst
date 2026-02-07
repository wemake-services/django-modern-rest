Authentication
==============

Enabling auth
-------------

Disabling auth
~~~~~~~~~~~~~~

TODO


Reusing pre-existing views
--------------------------

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

  To use ``jwt`` you must install ``'django-modern-rest[jwt]'`` extra.


.. autoclass:: django_modern_rest.security.jwt.JWTToken
  :members:

.. autoclass:: django_modern_rest.security.jwt.JWTSyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.jwt.JWTAsyncAuth
  :members:
  :inherited-members:

Pre-defined views to fetch JWT tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: django_modern_rest.security.jwt.views.ObtainTokensSyncController
  :members: post, login, make_response_payload, create_token, make_token_headers, convert_auth_payload

.. autoclass:: django_modern_rest.security.jwt.views.ObtainTokensAsyncController
  :members: post, login, make_response_payload, create_token, make_token_headers, convert_auth_payload

.. autoclass:: django_modern_rest.security.jwt.views.ObtainTokensPayload
  :members:
  :show-inheritance:

.. autoclass:: django_modern_rest.security.jwt.views.ObtainTokensResponse
  :members:
  :show-inheritance:
