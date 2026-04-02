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

We provide two classes to require JWT auth in your API:

- :class:`~dmr.security.jwt.auth.JWTSyncAuth` for sync views
- :class:`~dmr.security.jwt.auth.JWTAsyncAuth` for async views

Example, how to use the auth class and how to get ``self.request.user``:

.. literalinclude:: /examples/auth/jwt/using_jwt.py
  :caption: views.py
  :linenos:
  :language: python


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
configurations of :attr:`dmr.security.jwt.auth.JWTSyncAuth`
to additionally validate ``aud`` and ``iss`` JWT token claims.

We want to be sure that this class is at the same time:

1. Easy enough to not write a lot of boilerplate code by default
2. Customizable enough to be able to change a lot of stuff that
   can be affected by existing business rules
3. Always type safe


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


API Reference
-------------

.. autoclass:: dmr.security.jwt.token.JWToken
  :members:

.. autoclass:: dmr.security.jwt.auth.JWTSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.jwt.auth.JWTAsyncAuth
  :members:
  :inherited-members:

.. autofunction:: dmr.security.jwt.auth.get_jwt

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

Blocklist app
~~~~~~~~~~~~~

.. autoclass:: dmr.security.jwt.blocklist.auth.JWTokenBlocklistSyncMixin
  :members:

.. autoclass:: dmr.security.jwt.blocklist.auth.JWTokenBlocklistAsyncMixin
  :members:
