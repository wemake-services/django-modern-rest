Token Auth
==========

.. autoclass:: dmr.security.token.HeaderTokenSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.token.HeaderTokenAsyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.token.CookieTokenSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.token.CookieTokenAsyncAuth
  :members:
  :inherited-members:

Helpers
~~~~~~~

.. autofunction:: dmr.security.token.request_token

.. autofunction:: dmr.security.token.token.get_token_hash

.. autofunction:: dmr.security.token.token.resolve_expiry

Interfaces
~~~~~~~~~~

.. autoclass:: dmr.security.token.token.TokenLikeSync
  :members:

.. autoclass:: dmr.security.token.token.TokenLikeAsync
  :members:

Ready-to-use views to fetch opaque tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.security.token.concrete_views.ObtainTokenSyncController
  :members: as_view, convert_auth_payload, make_api_response

.. autoclass:: dmr.security.token.concrete_views.ObtainTokenAsyncController
  :members: as_view, convert_auth_payload, make_api_response

Pre-defined views to fetch opaque tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.security.token.views.ObtainTokenSyncController
  :members: post, login, make_api_response, issue_token, convert_auth_payload, make_token_name

.. autoclass:: dmr.security.token.views.ObtainTokenAsyncController
  :members: post, login, make_api_response, issue_token, convert_auth_payload, make_token_name

.. autoclass:: dmr.security.token.views.ObtainTokenPayload
  :members:
  :show-inheritance:

.. autoclass:: dmr.security.token.views.ObtainTokenResponse
  :members:
  :show-inheritance:

Default app
~~~~~~~~~~~

.. autoclass:: dmr.security.token.app.models.Token
  :members:
