JWT Auth
========

Docs: https://jwt.io

.. important::

  To use ``jwt`` you must install ``'django-modern-rest[jwt]'`` extra.


Requiring auth
--------------

.. note::

  Current user will always be accessible as ``self.request.user``.

  Read more: https://docs.djangoproject.com/en/stable/topics/auth/default/

We provide several classes to require JWT auth in your API,
depending on where the token is transferred.

Which one do you need?

.. list-table::
  :header-rows: 1
  :widths: 22 39 39

  * -
    - Token in headers
    - Token in cookies
  * - Classes
    - :class:`~dmr.security.jwt.auth.HeaderJWTSyncAuth`,
      :class:`~dmr.security.jwt.auth.HeaderJWTAsyncAuth`
    - :class:`~dmr.security.jwt.cookie.CookieJWTSyncAuth`,
      :class:`~dmr.security.jwt.cookie.CookieJWTAsyncAuth`
  * - Best for
    - Mobile apps, server-to-server calls, and SPAs
      that keep the token in memory
    - Browser apps where JavaScript must never
      touch the token at all
  * - Sent by the browser automatically
    - No, the client attaches the header itself
    - Yes, on every matching request
  * - Readable by JavaScript
    - Yes, the client stores the token itself
    - No, when the cookie is issued with ``httponly=True``
  * - If your page gets XSS-ed
    - The token can be read and stolen
    - The cookie cannot be read, though requests
      can still be made on the user's behalf
  * - CSRF
    - Not applicable
    - Enforced by us, needs ``CsrfViewMiddleware``
  * - Cross-origin setup
    - Just send the header
    - Needs ``SameSite``, ``Secure``, and CORS care

When in doubt, use headers. Reach for cookies when the requirement
is specifically "the frontend must not be able to read the token".

.. tabs::

  .. tab:: Token in headers

    When in doubt, use this as the default way to receive tokens.

    Use :class:`~dmr.security.jwt.auth.HeaderJWTSyncAuth` for sync views
    and :class:`~dmr.security.jwt.auth.HeaderJWTAsyncAuth` for async views.

    They are also available under their older names,
    ``JWTSyncAuth`` and ``JWTAsyncAuth``.

    You can customize:

    - Security scheme name, default: ``jwt``
    - Header name, default: ``Authorization``
    - Header value prefix, default: ``Bearer``
    - :meth:`Advanced jwt parameters <dmr.security.jwt.token.JWToken.decode>`

    Example, how to use the auth class and how to get ``self.request.user``:

    .. literalinclude:: /examples/auth/jwt/using_jwt.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: Token in cookies

    Use :class:`~dmr.security.jwt.cookie.CookieJWTSyncAuth` for sync views
    and :class:`~dmr.security.jwt.cookie.CookieJWTAsyncAuth` for async views.

    Unlike the ``Authorization`` header, the cookie stores
    the encoded token as-is, without any ``Bearer`` prefix.

    .. note::

      We enforce CSRF for this auth as well.
      See also: https://docs.djangoproject.com/en/stable/ref/csrf

      CSRF is only checked when the cookie is actually present,
      so that requests without it can still fall through
      to the next auth in the chain.

    You can customize:

    - Security scheme name, default: ``jwt``
    - Cookie name, default: ``access_token``
    - :meth:`Advanced jwt parameters <dmr.security.jwt.token.JWToken.decode>`

    .. literalinclude:: /examples/auth/jwt/using_jwt_cookie.py
      :caption: views.py
      :linenos:
      :language: python

Custom user models are automatically supported.

.. tip::

  Auth classes are tried in order, so you can accept both transports
  at once with ``auth = (CookieJWTSyncAuth(), JWTSyncAuth())``.
  The cookie auth returns ``None`` when its cookie is missing,
  which lets the header auth run next.

Customizing auth
~~~~~~~~~~~~~~~~

JWT Auth supports a lot of customization options:
starting from ``leeway`` and ``claim`` verification
up to the secret key customization.

See :meth:`~dmr.security.jwt.token.JWToken.decode`
for more info on all configuration options.


Reusing pre-existing views
--------------------------

We provide several pre-existing views to get auth tokens.
So, users won't have to write tons of boilerplate code.


JWT with access and refresh tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We provide two :ref:`reusable-controllers` to obtain
pairs of access and refresh tokens:

1. :class:`~dmr.security.jwt.views.ObtainTokensSyncController`
   for sync controllers
2. :class:`~dmr.security.jwt.views.ObtainTokensAsyncController`
   for async controllers

To use them, you will need to:

1. Provide actual types for serializer, request model, and response body
2. Redefine
   :meth:`~dmr.security.jwt.views.ObtainTokensSyncController.convert_auth_payload`
   to convert your request model into the kwargs
   of :func:`django.contrib.auth.authenticate` to authenticate your request
3. Redefine
   :meth:`~dmr.security.jwt.views.ObtainTokensSyncController.make_api_response`
   to return the response in the format of your choice

.. literalinclude:: /examples/auth/jwt/jwt_obtain_tokens.py
  :caption: views.py
  :linenos:
  :language: python

In this example we utilize pre-defined types of request model and response body,
only doing the bare minimum with no customizations.

Things that you can customize:

- Request body format
- Response body format
- JWT settings
- JWT token class to be :class:`~dmr.security.jwt.token.JWToken`
  subclass with custom logic
- Error messages, see :ref:`customizing-error-messages`
- Error handling, see :doc:`../error-handling`
- Response status code and any other regular controller or endpoint features

Here's an example with a lot more customizations:

.. literalinclude:: /examples/auth/jwt/jwt_complex_tokens.py
  :caption: views.py
  :linenos:
  :language: python

This example also provides issuer and audience in the token,
so it can be used together with ``accepted_issuers`` and ``accepted_audiences``
configurations of :class:`~dmr.security.jwt.auth.HeaderJWTSyncAuth`
to additionally validate ``aud`` and ``iss`` JWT token claims.

We want to be sure that this class is at the same time:

1. Easy enough to not write a lot of boilerplate code by default
2. Customizable enough to be able to change a lot of stuff that
   can be affected by existing business rules
3. Always type safe

Refreshing tokens
~~~~~~~~~~~~~~~~~

Once a user has a refresh token, they can use it to obtain a new pair
of access and refresh tokens without re-authenticating.
We provide two :ref:`reusable-controllers` for this:

1. :class:`~dmr.security.jwt.views.RefreshTokenSyncController`
   for sync controllers
2. :class:`~dmr.security.jwt.views.RefreshTokenAsyncController`
   for async controllers

To use them, you only need to:

1. Provide actual types for serializer, request payload, and response body
2. Redefine
   :meth:`~dmr.security.jwt.views.RefreshTokenSyncController.convert_refresh_payload`
   to extract the refresh token string from your request payload
3. Redefine
   :meth:`~dmr.security.jwt.views.RefreshTokenSyncController.make_api_response`
   to return the new token pair in the format of your choice

The controller validates that the submitted token:

- Is a valid, non-expired JWT signed with the configured secret
- Has ``extras.type == 'refresh'`` (i.e. it is a refresh token, not an access token)
- Belongs to an existing, active user

.. literalinclude:: /examples/auth/jwt/jwt_refresh_tokens.py
  :caption: views.py
  :linenos:
  :language: python

Verifying tokens
~~~~~~~~~~~~~~~~

Sometimes you need a dedicated endpoint to check whether an access token
is still valid, without accessing any protected resource.
We provide two :ref:`reusable-controllers` for this:

1. :class:`~dmr.security.jwt.views.VerifyTokenSyncController`
   for sync controllers
2. :class:`~dmr.security.jwt.views.VerifyTokenAsyncController`
   for async controllers

To use them, you only need to:

1. Provide actual types for serializer and request payload
2. Redefine
   :meth:`~dmr.security.jwt.views.VerifyTokenSyncController.convert_verify_payload`
   to extract the access token string from your request payload

The controller validates that the submitted token:

- Is a valid, non-expired JWT signed with the configured secret
- Has ``extras.type == 'access'`` (i.e. it is an access token, not a refresh one)
- Belongs to an existing, active user

On success it returns an empty ``204 No Content`` response.
On any validation failure it returns ``401 Unauthorized``.

.. literalinclude:: /examples/auth/jwt/jwt_verify_tokens.py
  :caption: views.py
  :linenos:
  :language: python


Issuing tokens as cookies
~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~dmr.security.jwt.cookie.CookieJWTSyncAuth`
and :class:`~dmr.security.jwt.cookie.CookieJWTAsyncAuth`
read tokens,
but something has to write them first.

.. todo::

  Provide a reusable controller that issues jwt tokens as cookies,
  the same way :class:`~dmr.security.jwt.views.ObtainTokensSyncController`
  issues them in the response body.
  Until then we deliberately ship no example here,
  because getting the cookie flags right is the whole point
  and an example is too easy to copy incorrectly.

.. danger::

  Always set ``httponly=True`` and ``secure=True`` on these cookies.
  Without ``httponly`` any XSS on your pages can read the token,
  and without ``secure`` it can leak over plain HTTP.

  Prefer ``samesite='strict'`` (or at least ``'lax'``)
  and scope the refresh token to the refresh endpoint's ``path``,
  so it is never sent to the rest of your API.

To log the user out, set the same cookies to an empty value
with ``max_age=0``, which tells the browser to drop them right away.
Blocklisting the access token on logout is a good idea too,
see :ref:`the section below <blocklisting-tokens>`.


.. _blocklisting-tokens:

Blocklisting tokens
-------------------

.. note::

  Add ``'dmr.security.jwt.blocklist'`` to the ``INSTALLED_APPS``
  if you want to use tokens blocklist.

JWT tokens might be leaked / outdated / etc.
There must be a way to make a valid, non-expired token blocked from auth.

To do so, we provide a default Django app to do so.
We store blocked tokens in the database
and provide an API to add tokens to the blocklist.

Here's an example:

.. literalinclude:: /examples/auth/jwt/blocklist_tokens.py
  :caption: views.py
  :linenos:
  :language: python

We provide two mixin types:

- :class:`~dmr.security.jwt.blocklist.auth.JWTokenBlocklistAsyncMixin`
  for async auth
- :class:`~dmr.security.jwt.blocklist.auth.JWTokenBlocklistSyncMixin`
  for sync auth

If this app is installed, we would provide an admin panel by default.

.. _cleaning-up-blocklisted-tokens:

Cleaning up expired tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~

The blocklist only answers one question:
is this *otherwise valid* token still allowed?
When ``exp`` of a token is in the past,
:meth:`~dmr.security.jwt.token.JWToken.decode` rejects it
before we even look into the blocklist.

Which means:

- Rows with ``expires_at`` in the future must stay,
  they are the ones actually blocking tokens
- Rows with ``expires_at`` in the past can be removed,
  they cannot change any auth decision anymore

Nothing removes them for us, so the table grows forever
while storing rows that can never affect auth again.
We recommend deleting them with a periodic job:

.. literalinclude:: /examples/auth/jwt/blocklist_cleanup.py
  :caption: myapp/management/commands/cleanup_blocklist.py
  :linenos:
  :language: python

Then run this task as a periodic job.

.. warning::

  Keep the grace period bigger than the largest ``leeway``
  you pass to your auth classes.
  With a non-zero ``leeway`` a token is still accepted
  for that many seconds after ``exp``,
  and its blocklist row is still doing real work for that long.

.. tip::

  The same reasoning applies to the opaque
  :class:`~dmr.security.token.app.models.Token` model,
  see :ref:`cleaning-up-old-tokens`.


API Reference
-------------

.. autoclass:: dmr.security.jwt.token.JWToken
  :members:

.. autoclass:: dmr.security.jwt.auth.HeaderJWTSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.jwt.auth.HeaderJWTAsyncAuth
  :members:
  :inherited-members:

.. note::

  Since version 0.15.0 ``JWTSyncAuth`` and ``JWTAsyncAuth`` are kept as aliases of
  :class:`~dmr.security.jwt.auth.HeaderJWTSyncAuth` and
  :class:`~dmr.security.jwt.auth.HeaderJWTAsyncAuth`.
  Existing code keeps working unchanged.

.. autoclass:: dmr.security.jwt.cookie.CookieJWTSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.jwt.cookie.CookieJWTAsyncAuth
  :members:
  :inherited-members:

.. autofunction:: dmr.security.jwt.auth.request_jwt

Pre-defined views to fetch JWT tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.security.jwt.views.ObtainTokensSyncController
  :members: post, login, make_api_response, create_jwt_token, convert_auth_payload, make_jwt_id

.. autoclass:: dmr.security.jwt.views.ObtainTokensAsyncController
  :members: post, login, make_api_response, create_jwt_token, convert_auth_payload, make_jwt_id

.. autoclass:: dmr.security.jwt.views.ObtainTokensPayload
  :members:
  :show-inheritance:

.. autoclass:: dmr.security.jwt.views.ObtainTokensResponse
  :members:
  :show-inheritance:

.. autoclass:: dmr.security.jwt.views.RefreshTokenSyncController
  :members: post, refresh, check_auth, convert_refresh_payload, make_api_response, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.RefreshTokenAsyncController
  :members: post, refresh, check_auth, convert_refresh_payload, make_api_response, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.RefreshTokenPayload
  :members:
  :show-inheritance:

.. autoclass:: dmr.security.jwt.views.VerifyTokenSyncController
  :members: post, verify, get_user, check_auth, convert_verify_payload, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.VerifyTokenAsyncController
  :members: post, verify, get_user, check_auth, convert_verify_payload, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.VerifyTokenPayload
  :members:
  :show-inheritance:

Blocklist app
~~~~~~~~~~~~~

.. autoclass:: dmr.security.jwt.blocklist.models.BlocklistedJWToken
  :members:

.. autoclass:: dmr.security.jwt.blocklist.auth.JWTokenBlocklistSyncMixin
  :members:

.. autoclass:: dmr.security.jwt.blocklist.auth.JWTokenBlocklistAsyncMixin
  :members:
