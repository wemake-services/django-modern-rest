JWT Auth
========

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

Ready-to-use views
~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.security.jwt.concrete_views.ObtainTokensSyncController
  :members: as_view, convert_auth_payload, make_api_response

.. autoclass:: dmr.security.jwt.concrete_views.ObtainTokensAsyncController
  :members: as_view, convert_auth_payload, make_api_response

.. autoclass:: dmr.security.jwt.concrete_views.RefreshTokenSyncController
  :members: as_view, convert_refresh_payload, make_api_response

.. autoclass:: dmr.security.jwt.concrete_views.RefreshTokenAsyncController
  :members: as_view, convert_refresh_payload, make_api_response

.. autoclass:: dmr.security.jwt.concrete_views.VerifyTokenSyncController
  :members: as_view, convert_verify_payload

.. autoclass:: dmr.security.jwt.concrete_views.VerifyTokenAsyncController
  :members: as_view, convert_verify_payload

.. autoclass:: dmr.security.jwt.concrete_views.CookieObtainTokensSyncController
  :members: as_view, convert_auth_payload

.. autoclass:: dmr.security.jwt.concrete_views.CookieObtainTokensAsyncController
  :members: as_view, convert_auth_payload

.. autoclass:: dmr.security.jwt.concrete_views.CookieRefreshTokensSyncController
  :members: as_view

.. autoclass:: dmr.security.jwt.concrete_views.CookieRefreshTokensAsyncController
  :members: as_view

.. autoclass:: dmr.security.jwt.concrete_views.CookieLogoutSyncController
  :members: as_view

.. autoclass:: dmr.security.jwt.concrete_views.CookieLogoutAsyncController
  :members: as_view

.. autodata:: dmr.security.jwt.concrete_views.DEFAULT_REFRESH_COOKIE_PATH

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
  :members: post, refresh, get_user, check_auth, convert_refresh_payload, make_api_response, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.RefreshTokenAsyncController
  :members: post, refresh, get_user, check_auth, convert_refresh_payload, make_api_response, create_jwt_token, make_jwt_id

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
  :members: post, login, convert_auth_payload, make_api_response, validate_spec, issue_cookies, access_cookie_spec, refresh_cookie_spec, response_headers, response_headers_spec, rotate_csrf_token, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.CookieObtainTokensAsyncController
  :members: post, login, convert_auth_payload, make_api_response, validate_spec, issue_cookies, access_cookie_spec, refresh_cookie_spec, response_headers, response_headers_spec, rotate_csrf_token, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.CookieRefreshTokensSyncController
  :members: post, refresh, get_user, check_auth, make_api_response, validate_spec, issue_cookies, response_headers, response_headers_spec, check_csrf, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.CookieRefreshTokensAsyncController
  :members: post, refresh, get_user, check_auth, make_api_response, validate_spec, issue_cookies, response_headers, response_headers_spec, check_csrf, create_jwt_token, make_jwt_id

.. autoclass:: dmr.security.jwt.views.CookieLogoutSyncController
  :members: post, logout, revoke_tokens, make_api_response, validate_spec, discard_cookies, response_headers, response_headers_spec, check_csrf

.. autoclass:: dmr.security.jwt.views.CookieLogoutAsyncController
  :members: post, logout, revoke_tokens, make_api_response, validate_spec, discard_cookies, response_headers, response_headers_spec, check_csrf

Blocklist app
~~~~~~~~~~~~~

.. autoclass:: dmr.security.jwt.blocklist.models.BlocklistedJWToken
  :members:

.. autoclass:: dmr.security.jwt.blocklist.auth.JWTokenBlocklistSyncMixin
  :members:

.. autoclass:: dmr.security.jwt.blocklist.auth.JWTokenBlocklistAsyncMixin
  :members:
