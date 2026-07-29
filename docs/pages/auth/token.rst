Token Auth
==========

Opaque token authentication backed by database hashed records.

.. note::

  To use token auth with the default
  :class:`~dmr.security.token.app.models.Token` model,
  add ``'dmr.security.token.app'`` to ``INSTALLED_APPS``
  and run migrations with ``manage.py migrate``.

  You can subclass all classes, change ``token_model`` property
  and substitute the token model for your own one.
  More on that later.


Requiring auth
--------------

.. note::

  Current user will always be accessible as ``self.request.user``.

  Read more: https://docs.djangoproject.com/en/stable/topics/auth/default/

We provide several classes to require token auth in your API
for both sync and async endpoints.

Example of requiring token auth and accessing
both ``self.request.user`` and the current token:

.. tabs::

  .. tab:: Token in headers

    Use :class:`~dmr.security.token.HeaderTokenSyncAuth` and
    :class:`~dmr.security.token.HeaderTokenAsyncAuth`
    for header-based auth.

    .. literalinclude:: /examples/auth/token/using_token_header.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: Token in cookies

    Use :class:`~dmr.security.token.CookieTokenSyncAuth` and
    :class:`~dmr.security.token.CookieTokenAsyncAuth`
    for cookie-based auth.

    .. note::

      We enforce CSRF for this auth as well.
      See also: https://docs.djangoproject.com/en/6.0/ref/csrf

    .. literalinclude:: /examples/auth/token/using_token_cookie.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: Token in query string

    Use :class:`~dmr.security.token.QueryTokenSyncAuth` and
    :class:`~dmr.security.token.QueryTokenAsyncAuth`
    for query-param based auth.

    .. warning::

      Sending tokens via query string is not really safe,
      because they can show up in access logs.

    .. literalinclude:: /examples/auth/token/using_token_query.py
      :caption: views.py
      :linenos:
      :language: python


Token lifecycle
---------------

.. mermaid::
  :caption: Token states
  :config: {"theme": "forest"}

  stateDiagram-v2
      [*] --> Active: TokenLike.issue / TokenLike.aissue
      Active --> Revoked: TokenLike.revoke / TokenLike.arevoke
      Revoked --> [*]
      Active --> Expired
      Expired --> [*]

All token instances are issued and revoked
via :class:`dmr.security.token.auth.base.TokenLike` interface.

Our default implementation :class:`dmr.security.token.app.models.Token`
strictly follows the interface.

Revoking a token
~~~~~~~~~~~~~~~~

Tokens can be revoked via helper methods:

- :meth:`~dmr.security.token.auth.base.TokenLike.revoke`
- :meth:`~dmr.security.token.auth.base.TokenLike.arevoke`

Here's an example with the default model:

.. literalinclude:: /examples/auth/token/revoke_token.py
  :caption: revoke_token.py
  :linenos:
  :language: python


Django admin
~~~~~~~~~~~~

When ``'dmr.security.token.app'`` is in ``INSTALLED_APPS``,
default :class:`~dmr.security.token.app.models.Token` model entries
are accessible from the Django admin for viewing, searching, filtering,
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
  We automatically enforce CSRF checks before any other actions are taken.
  Using cookie-based auth without CSRF is not secure.

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

Default app
~~~~~~~~~~~

.. autoclass:: dmr.security.token.app.models.Token
  :members:
