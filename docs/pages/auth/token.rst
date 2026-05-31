Token Auth
==========

Opaque token authentication backed by database records.

.. note::

  To use token auth, add ``'dmr.security.token'`` to ``INSTALLED_APPS``
  and run migrations.


Requiring auth
--------------

.. note::

  Current user will always be accessible as ``self.request.user``.

  Read more: https://docs.djangoproject.com/en/stable/topics/auth/default/

We provide several classes to require token auth in your API:

- :class:`~dmr.security.token.TokenSyncAuth` for sync views
- :class:`~dmr.security.token.TokenAsyncAuth` for async views
- :class:`~dmr.security.token.QueryTokenSyncAuth` and
  :class:`~dmr.security.token.QueryTokenAsyncAuth`
  for query-param based auth
- :class:`~dmr.security.token.CookieTokenSyncAuth` and
  :class:`~dmr.security.token.CookieTokenAsyncAuth`
  for cookie-based auth

Example of requiring token auth and accessing
both ``self.request.user`` and the current token:

.. literalinclude:: /examples/auth/token/using_token_header.py
  :caption: views.py
  :linenos:
  :language: python


Token lifecycle
---------------

Tokens are created via :class:`~dmr.security.token.models.Token`
manager methods:

- :meth:`~dmr.security.token.models.TokenManager.create_token`
- :meth:`~dmr.security.token.models.TokenManager.acreate_token`

Both methods return ``(token_instance, raw_token)``.
Only token hash is stored in the database.

You can revoke tokens with:

- :meth:`~dmr.security.token.models.Token.revoke`
- :meth:`~dmr.security.token.models.Token.arevoke`

.. literalinclude:: /examples/auth/token/token_lifecycle.py
  :caption: token_lifecycle.py
  :linenos:
  :language: python


Configuration notes
-------------------

Opaque tokens can be sent by clients in three common ways:

1. Query parameter
2. Header
3. Cookie

Example request shapes:

.. code-block:: text

  GET /api/thing?token=abc123

.. code-block:: text

  GET /api/thing HTTP/1.1
  X-API-Token: abc123

.. code-block:: text

  GET /api/thing HTTP/1.1
  Cookie: token=abc123

Use these auth classes for each transport:

- Query param: :class:`~dmr.security.token.QueryTokenSyncAuth` /
  :class:`~dmr.security.token.QueryTokenAsyncAuth`
- Header: :class:`~dmr.security.token.TokenSyncAuth` /
  :class:`~dmr.security.token.TokenAsyncAuth`
- Cookie: :class:`~dmr.security.token.CookieTokenSyncAuth` /
  :class:`~dmr.security.token.CookieTokenAsyncAuth`

By default, header auth expects:

- ``X-API-Token: <raw_token>``

You can customize behavior per auth instance,
for example to support ``Authorization`` header styles:

- ``TokenSyncAuth(header_name='Authorization', prefix='Token')``
- ``TokenSyncAuth(header_name='Authorization', prefix='Bearer')``

.. warning::

  Query param auth leaks tokens into logs, browser history,
  and ``Referer`` headers. Prefer header-based auth.

.. warning::

  Cookie auth is CSRF-sensitive in browser-facing contexts.
  Ensure ``django.middleware.csrf.CsrfViewMiddleware`` is enabled.


API Reference
-------------

.. autoclass:: dmr.security.token.TokenSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.token.TokenAsyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.token.QueryTokenSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.token.QueryTokenAsyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.token.CookieTokenSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.token.CookieTokenAsyncAuth
  :members:
  :inherited-members:

.. autofunction:: dmr.security.token.request_token

.. autoclass:: dmr.security.token.models.TokenManager
  :members:

.. autoclass:: dmr.security.token.models.Token
  :members:
