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
    - :class:`~dmr.security.jwt.auth.CookieJWTSyncAuth`,
      :class:`~dmr.security.jwt.auth.CookieJWTAsyncAuth`
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

    Use :class:`~dmr.security.jwt.auth.CookieJWTSyncAuth` for sync views
    and :class:`~dmr.security.jwt.auth.CookieJWTAsyncAuth` for async views.

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
  at once with ``auth = (CookieJWTSyncAuth(), HeaderJWTSyncAuth())``.
  The cookie auth returns ``None`` when its cookie is missing,
  which lets the header auth run next.

Customizing auth
~~~~~~~~~~~~~~~~

JWT Auth supports a lot of customization options:
starting from ``leeway`` and ``claim`` verification
up to the secret key customization.

See :meth:`~dmr.security.jwt.token.JWToken.decode`
for more info on all configuration options.

.. _jwt-json-backend:

JSON backend
~~~~~~~~~~~~

Token payloads are encoded and decoded with the same JSON backend
we use for parsers and renderers: ``msgspec`` when it is installed,
native pure Python :mod:`json` otherwise.
See :ref:`alternative-json` for the details.

Since JWT auth runs on every authenticated request,
having ``msgspec`` installed makes
:meth:`~dmr.security.jwt.token.JWToken.encode` and
:meth:`~dmr.security.jwt.token.JWToken.decode` noticeably faster.

.. warning::

  Registered claims are always encoded the same way,
  but ``extras`` can hold arbitrary values.
  Only json-native values there
  (``str``, ``int``, ``float``, ``bool``, ``None``, ``list``, and ``dict``)
  are guaranteed to produce identical tokens
  with and without ``msgspec`` installed.
  Other types, like :class:`~datetime.timedelta` or :class:`set`,
  are either encoded differently or not supported at all
  by the pure Python fallback.
  Keep ``extras`` json-native when your tokens are issued
  and verified by different installs.


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


.. _issuing-tokens-as-cookies:

Issuing tokens as cookies
~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~dmr.security.jwt.auth.CookieJWTSyncAuth`
and :class:`~dmr.security.jwt.auth.CookieJWTAsyncAuth`
read tokens, and these :ref:`reusable-controllers` write them.
They are the cookie counterparts of the controllers above:
same jwt settings, same hooks, but the tokens end up
in ``Set-Cookie`` instead of the response body.

1. :class:`~dmr.security.jwt.views.CookieObtainTokensSyncController`
   authenticates the user and sets both cookies
2. :class:`~dmr.security.jwt.views.CookieRefreshTokensSyncController`
   reads the refresh cookie and rotates both cookies
3. :class:`~dmr.security.jwt.views.CookieLogoutSyncController`
   sends both cookies back empty and already expired

Every one of them has an ``Async`` version as well.

.. tabs::

  .. tab:: Obtain

    .. literalinclude:: /examples/auth/jwt/jwt_cookie_obtain.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: Refresh

    Rotating tokens takes no request body at all:
    the browser sends the refresh cookie on its own.

    .. literalinclude:: /examples/auth/jwt/jwt_cookie_refresh.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: Log out

    .. literalinclude:: /examples/auth/jwt/jwt_cookie_logout.py
      :caption: views.py
      :linenos:
      :language: python

``jwt_refresh_cookie_path`` is the only required setting,
and it has no default on purpose:
it scopes the refresh cookie to your refresh endpoint,
so the refresh token is not sent with any other request.
Pass ``'/'`` if you really want it everywhere.

Everything else already has a safe default:

.. list-table::
  :header-rows: 1
  :widths: 34 22 44

  * - Attribute
    - Default
    - What it does
  * - ``jwt_access_cookie``
    - ``'access_token'``
    - Name of the access token cookie, must match ``cookie_name``
      of the auth class that reads it
  * - ``jwt_refresh_cookie``
    - ``'refresh_token'``
    - Name of the refresh token cookie
  * - ``jwt_access_cookie_path``
    - ``'/'``
    - ``path`` of the access token cookie
  * - ``jwt_refresh_cookie_path``
    - required
    - ``path`` of the refresh token cookie
  * - ``jwt_cookie_domain``
    - ``None``
    - ``domain`` of both cookies
  * - ``jwt_cookie_secure``
    - ``True``
    - Only send both cookies over https
  * - ``jwt_cookie_httponly``
    - ``True``
    - Hide both cookies from javascript
  * - ``jwt_cookie_samesite``
    - ``'lax'``
    - ``samesite`` policy of both cookies
  * - ``jwt_ensure_csrf``
    - ``True``
    - Check CSRF on refresh and logout

The cookies live exactly as long as the tokens inside them:
``max-age`` comes from ``jwt_expiration``
and ``jwt_refresh_expiration``.

.. danger::

  ``httponly=True`` and ``secure=True`` are the whole point of this flow.
  Without ``httponly`` any XSS on your pages can read the token,
  and without ``secure`` it can leak over plain HTTP.
  Only weaken ``samesite`` to ``'none'``
  when your frontend really is on another site.

There is no response body by default: the tokens are already in the cookies,
and sending them in the body as well would hand them
to any script on the page. When you do need a body,
pass its type as the last type argument and change the status code:

.. code:: python

  class ObtainCookiesController(
      CookieObtainTokensSyncController[
          PydanticSerializer,
          ObtainTokensPayload,
          UserModel,  # response body type
      ],
  ):
      response_status_code = HTTPStatus.OK
      jwt_refresh_cookie_path = '/api/auth/refresh/'

      @override
      def make_api_response(self) -> UserModel: ...

CSRF and logout
^^^^^^^^^^^^^^^

Refresh and logout act on cookies alone, and browsers send cookies
on their own. So both endpoints run the same CSRF check
that :class:`~dmr.security.jwt.auth.CookieJWTSyncAuth` runs,
and both document the ``403`` response it can raise.
The login endpoint does not: it needs credentials in the body,
and it issues a fresh CSRF token for the frontend to use
on every request after it.

Logging out is transport-only by default: the cookies are dropped,
but a token that leaked before the logout stays valid until it expires.
Override
:meth:`~dmr.security.jwt.views.CookieLogoutSyncController.revoke_tokens`
to also blocklist it, see :ref:`blocklisting-tokens`:

.. literalinclude:: /examples/auth/jwt/jwt_cookie_logout_blocklist.py
  :caption: views.py
  :linenos:
  :language: python


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

.. important::

  Both mixins add ``'jti'`` to ``require_claims`` of the auth class
  they are mixed into, on top of whatever you pass yourself.

  Blocklist rows are keyed by ``jti``, so a token without one
  can never be blocklisted. Accepting such tokens would mean
  that the blocklist is silently bypassed:
  the lookup would match no rows and the token would stay valid forever.
  We reject them with ``401`` instead.

  If you issue tokens with the controllers we ship, make sure that
  :meth:`~dmr.security.jwt.views.ObtainTokensSyncController.make_jwt_id`
  returns a value, our default implementation already does.

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

.. autoexception:: dmr.security.jwt.token.JWTokenError
  :members:
  :show-inheritance:

Header auth
~~~~~~~~~~~

.. autoclass:: dmr.security.jwt.auth.HeaderJWTSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.jwt.auth.HeaderJWTAsyncAuth
  :members:
  :inherited-members:

.. note::

  Since version 0.15.0 ``JWTSyncAuth`` and ``JWTAsyncAuth``
  are kept as aliases of
  :class:`~dmr.security.jwt.auth.HeaderJWTSyncAuth` and
  :class:`~dmr.security.jwt.auth.HeaderJWTAsyncAuth`.
  Existing code keeps working unchanged.
  They are soft-deprecated and will be removed before the ``1.0.0`` release.
  Do not use them.

Cookie auth
~~~~~~~~~~~

.. autoclass:: dmr.security.jwt.auth.CookieJWTSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.jwt.auth.CookieJWTAsyncAuth
  :members:
  :inherited-members:

Helpers
~~~~~~~

.. autofunction:: dmr.security.jwt.auth.request_jwt

.. autofunction:: dmr.security.jwt.auth.set_request_attrs

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

Pre-defined views to issue JWT tokens as cookies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.security.jwt.views.CookieObtainTokensSyncController
  :members: post, login, convert_auth_payload, make_api_response, issue_cookies, access_cookie_spec, refresh_cookie_spec, rotate_csrf_token, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.CookieObtainTokensAsyncController
  :members: post, login, convert_auth_payload, make_api_response, issue_cookies, access_cookie_spec, refresh_cookie_spec, rotate_csrf_token, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.CookieRefreshTokensSyncController
  :members: post, refresh, get_user, check_auth, make_api_response, issue_cookies, check_csrf, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.CookieRefreshTokensAsyncController
  :members: post, refresh, get_user, check_auth, make_api_response, issue_cookies, check_csrf, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.CookieLogoutSyncController
  :members: post, logout, revoke_tokens, make_api_response, discard_cookies, check_csrf

.. autoclass:: dmr.security.jwt.views.CookieLogoutAsyncController
  :members: post, logout, revoke_tokens, make_api_response, discard_cookies, check_csrf

Blocklist app
~~~~~~~~~~~~~

.. autoclass:: dmr.security.jwt.blocklist.models.BlocklistedJWToken
  :members:

.. autoclass:: dmr.security.jwt.blocklist.auth.JWTokenBlocklistSyncMixin
  :members:

.. autoclass:: dmr.security.jwt.blocklist.auth.JWTokenBlocklistAsyncMixin
  :members:
