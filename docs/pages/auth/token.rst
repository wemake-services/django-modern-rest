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

We provide several classes to require token auth in your API
for both sync and async endpoints:

- :class:`~dmr.security.token.HeaderTokenSyncAuth` and
  :class:`~dmr.security.token.HeaderTokenAsyncAuth`
  for header-based auth
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

:class:`dmr.security.token.models.Token` instances
are issued and revoked via dedicated functions sync and async functions:

- :func:`dmr.security.token.logic.token_create` /
  :func:`dmr.security.token.logic.token_acreate` to create tokens
- :func:`dmr.security.token.logic.token_revoke` /
  :func:`dmr.security.token.logic.token_arevoke` to revoke tokens

Creation helpers return ``(token_instance, raw_token)``.
Only the token hash is stored in the database,
the raw token is returned exactly once and never persisted.

:class:`~dmr.security.token.models.Token` has two
:class:`~django.db.models.DateTimeField` fields that gate validity:

- ``expires_at`` — set once,
  at creation
- ``revoked_at`` — ``None``
  until :func:`~dmr.security.token.logic.token_revoke` is called

On each authenticated request, the auth backend:

1. Hashes the incoming raw token and looks up the matching row.
   If no row matches, authentication fails with a ``401``
2. Checks that the token is still active (neither revoked nor expired)
3. Checks that the associated user account is still active
    (``is_active``)

If any check fails, authentication fails with a ``401``
and no token state is changed.

.. note::

  Revoking a token is a write: it sets ``revoked_at`` on the row.
  Expiry needs no write at all, ``expires_at`` is set once up front
  and simply compared against the clock on every lookup from then on.

  Successful authentication can *also* write to the row,
  see :ref:`tracking-last-use` below.

.. mermaid::
  :caption: Token states
  :config: {"theme": "forest"}

  stateDiagram-v2
      [*] --> Active: token_create / token_acreate
      Active --> Revoked: token_revoke / token_arevoke
      Revoked --> [*]

Issuing a token
~~~~~~~~~~~~~~~

Issuing a token has to be gated by some pre-existing trust,
not by the token itself, otherwise a client would need a token
to get a token. That pre-existing trust is specific to your
application, so we don't ship a built-in way to issue tokens.
Call :func:`~dmr.security.token.logic.token_create` directly,
for example from a Django shell:

.. literalinclude:: /examples/auth/token/issue_token.py
  :caption: issue_token.py
  :linenos:
  :language: python

.. important::

  ``raw_token`` is only available here, right after creation.
  Only its hash is stored, so save it now, it cannot be recovered later.

.. note::

  If you want to issue tokens from an HTTP endpoint, for example
  a "generate API key" button in a dashboard, gate it behind
  an auth method other than the token being issued.
  :class:`~dmr.security.django_session.auth.DjangoSessionSyncAuth`
  is a common choice, since the user already has a session
  from logging in.

Revoking a token
~~~~~~~~~~~~~~~~

Tokens can be revoked via helper functions:

- :func:`~dmr.security.token.logic.token_revoke`
- :func:`~dmr.security.token.logic.token_arevoke`

.. literalinclude:: /examples/auth/token/revoke_token.py
  :caption: revoke_token.py
  :linenos:
  :language: python


Django admin
~~~~~~~~~~~~

When ``'dmr.security.token'`` is in ``INSTALLED_APPS``, tokens are
accessible from the Django admin for viewing, searching, filtering,
and revocation.

.. note::

  Token creation is intentionally disabled in the admin.
  :func:`~dmr.security.token.logic.token_create` returns the raw
  token exactly once and an admin form has no way to surface
  that value. Use :func:`~dmr.security.token.logic.token_create`
  directly to issue tokens instead.

Active tokens can be revoked individually from the change form,
or in bulk using the **Revoke selected tokens** action from the
change list.


.. _tracking-last-use:

Tracking last use
------------------

Auth classes accept an ``update_last_used`` flag for tracking
when a token was last successfully used. It is opt-in,
defaulting to ``False``:

.. code-block:: python

  HeaderTokenSyncAuth(update_last_used=True)

When enabled, every successful authentication writes
``last_used_at`` and ``updated_at`` back to the token's row.

.. warning::

  Enabling this turns every authenticated request into a database
  write, not just token creation and revocation. On high-traffic
  endpoints this can meaningfully increase database load.

  If you need last-used tracking but want to control the write cost,
  consider:

  - throttling writes to at most once per interval
    (for example, only updating if the existing ``last_used_at``
    is older than a few minutes)
  - writing out-of-band, for example via a task queue,
    instead of inline in the request path
  - leaving it disabled (the default) and relying
    on application-level logging or analytics instead


Choosing a transport
---------------------

Opaque tokens can be sent by clients in three ways.
Pick the transport that matches your client.

Header
~~~~~~

.. code-block:: text

  GET /api/thing HTTP/1.1
  X-API-Token: abc123

Classes: :class:`~dmr.security.token.HeaderTokenSyncAuth` /
:class:`~dmr.security.token.HeaderTokenAsyncAuth`.

By default, header auth expects ``X-API-Token: <raw_token>``.
You can customize the header name and prefix to match
other conventions, for example:

.. code-block:: python

  # DRF-compatible token auth: Authorization: Token <raw_token>
  HeaderTokenSyncAuth(header_name='Authorization', prefix='Token')

  # Bearer-style auth: Authorization: Bearer <raw_token>
  HeaderTokenSyncAuth(header_name='Authorization', prefix='Bearer')

Cookie
~~~~~~

.. code-block:: text

  GET /api/thing HTTP/1.1
  Cookie: token=abc123

Classes: :class:`~dmr.security.token.CookieTokenSyncAuth` /
:class:`~dmr.security.token.CookieTokenAsyncAuth`.

.. warning::

  Cookie auth is CSRF-sensitive in browser-facing contexts.
  Ensure ``django.middleware.csrf.CsrfViewMiddleware`` is enabled.

Query parameter
~~~~~~~~~~~~~~~~

.. code-block:: text

  GET /api/thing?token=abc123

Classes: :class:`~dmr.security.token.QueryTokenSyncAuth` /
:class:`~dmr.security.token.QueryTokenAsyncAuth`.

.. warning::

  Query param auth leaks tokens into server logs, browser history,
  and ``Referer`` headers. Prefer header-based auth whenever possible.


API Reference
-------------

.. autoclass:: dmr.security.token.HeaderTokenSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.token.HeaderTokenAsyncAuth
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

.. autofunction:: dmr.security.token.logic.token_create

.. autofunction:: dmr.security.token.logic.token_acreate

.. autofunction:: dmr.security.token.logic.token_revoke

.. autofunction:: dmr.security.token.logic.token_arevoke

.. autoclass:: dmr.security.token.models.Token
  :members:
