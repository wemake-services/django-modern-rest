django-allauth
==============

Docs: https://docs.allauth.org/en/latest/headless/index.html

.. important::

  To use ``allauth`` features you must install ``django-allauth`` separatly.

``django-allauth`` is a well-established, full-featured library that already
solves the hard parts of auth: registration, email verification, password
reset, social login, MFA, and passkeys. Its `headless
<https://docs.allauth.org/en/latest/headless/index.html>`_ mode exposes all
of that over a plain JSON API that is not coupled to any REST framework.

So we do not reimplement any of it. Instead:

1. ``django-allauth`` owns the login flow and hands out session tokens
2. ``django-modern-rest`` turns those tokens
   into an authed ``self.request.user`` on your own endpoints

.. note::

  Add ``'allauth'``, ``'allauth.account'``, and ``'allauth.headless'``
  to ``INSTALLED_APPS``, and
  ``'allauth.account.middleware.AccountMiddleware'`` to ``MIDDLEWARE``.

  See the `allauth installation docs
  <https://docs.allauth.org/en/latest/installation/quickstart.html>`_.


How it works
------------

In headless mode ``django-allauth`` supports two client types.
Session tokens are used by the ``app`` client, which is the one
you want for mobile apps and other non-browser API consumers.

.. mermaid::
  :caption: Session token flow
  :config: {"theme": "forest"}

  sequenceDiagram
      participant C as Client
      participant A as django-allauth
      participant D as Your dmr API

      C->>A: POST /_allauth/app/v1/auth/login
      A-->>C: X-Session-Token
      C->>D: GET /api/me/ (X-Session-Token)
      D->>D: XSessionTokenSyncAuth resolves the token
      D-->>C: 200, authed as request.user

The login half is served by ``django-allauth`` itself.


Routing the headless views
~~~~~~~~~~~~~~~~~~~~~~~~~~

``django-allauth`` ships the login and session endpoints as ordinary
Django views, so you can mount them into your own :class:`~dmr.routing.Router`
with :func:`~dmr.routing.external_path` and describe them in your own
OpenAPI schema. See :ref:`external views <external-views>` for the details.

``LoginView`` hands out the session token, ``SessionView`` inspects it
on ``GET`` and logs out on ``DELETE``. Both need to know which headless
client they serve, and session tokens only exist for the ``app`` one:

.. literalinclude:: /examples/auth/allauth/allauth_external_views.py
  :caption: urls.py
  :linenos:
  :emphasize-lines: 19-32
  :language: python

Your own endpoints then sit behind
:class:`~dmr.security.allauth.auth.XSessionTokenSyncAuth`,
as shown :ref:`below <allauth-requiring-auth>`.

.. warning::

  Describing a third-party view in your schema makes it part of your
  API contract, including for schema-driven tests.
  ``django-allauth``'s views do not always fit a strict contract:
  the login view answers ``400`` instead of ``405`` for unsupported
  methods, and returns ``500`` for a JSON body that is not an object.
  Pass ``openapi=None`` to route such a view without publishing it.


.. _allauth-requiring-auth:

Requiring auth
--------------

.. note::

  Current user will always be accessible as ``self.request.user``.

  Read more: https://docs.djangoproject.com/en/stable/topics/auth/default/

We provide two classes to require an ``allauth`` session token:

- :class:`~dmr.security.allauth.auth.XSessionTokenSyncAuth` for sync views
- :class:`~dmr.security.allauth.auth.XSessionTokenAsyncAuth` for async views

.. literalinclude:: /examples/auth/allauth/using_allauth.py
  :caption: views.py
  :linenos:
  :language: python

Custom user models are automatically supported.

You can customize:

- Security scheme name, default: ``session_token``
- Header name, default: ``X-Session-Token``
- :meth:`~dmr.security.allauth.auth.XSessionTokenSyncAuth.get_session_token`
  to read the token from somewhere else entirely,
  for example from the ``Authorization`` header

.. note::

  Tokens are read from a header, never from a cookie.
  Browsers do not attach headers automatically on cross-site requests,
  so unlike :doc:`django-session` there is no CSRF check here.

Accessing the allauth session
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``django-allauth`` resolves a token into a Django session object.
Use :func:`~dmr.security.allauth.auth.request_allauth_session`
if you need to read anything from it.

.. warning::

  This is the session the token resolved into,
  not :attr:`django.http.HttpRequest.session` of the current request.
  We do not log the user into the current session,
  because that would issue a session cookie for a cookie-less API.


Async support
-------------

``django-allauth`` has no async API at the moment, so
:class:`~dmr.security.allauth.auth.XSessionTokenAsyncAuth` runs
the session lookup in a threadpool via ``asgiref.sync.sync_to_async``.

It works correctly, but it does not give you the full benefit
of async I/O. If that matters for your workload, prefer
:doc:`token` or :doc:`jwt`, which use native async ORM calls.


Trade-offs
----------

Things worth knowing before choosing this auth:

- ``django-allauth`` is an extra dependency, and a fairly large one
- We call ``allauth.headless.internal.sessionkit``, which lives in
  ``allauth``'s internal namespace. This is the same entry point that
  ``allauth``'s own Django REST Framework and Django Ninja integrations
  use, so it is stable in practice, but it is not a public API contract
- Session tokens are Django sessions underneath, so they are stored
  in whatever ``SESSION_ENGINE`` you configured, and hitting the API
  costs a session store lookup per request

If you only need plain token auth without ``allauth``'s account features,
:doc:`token` is simpler and has no third-party dependency.


API Reference
-------------

.. autoclass:: dmr.security.allauth.auth.XSessionTokenSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.allauth.auth.XSessionTokenAsyncAuth
  :members:
  :inherited-members:

.. autofunction:: dmr.security.allauth.auth.request_allauth_session
