How authentication works
========================

``django-modern-rest`` supports different auth workflows.

We support both:

1. Checking that user requests contain required auth credentials
2. Boilerplate code for views that provide credentials for users


Enabling auth
-------------

Let's start with how auth can be enabled and how it works.

There are two main base classes for auth:

1. :class:`~dmr.security.SyncAuth` for sync controllers
2. :class:`~dmr.security.AsyncAuth` for async controllers

.. warning::

  Sync controllers can't directly use async auth.
  And async controllers can't directly use sync auth.

All auth - that we are going to use - will be instances of these two classes
(and their subclasses).

All of them have unified API:

- ``__init__`` method contains configuration that can be changed per instance
- :meth:`~dmr.security.SyncAuth.__call__` does all
  the heavy lifting. If ``__call__`` returns anything but ``None``,
  then we consider auth instance to succeed. If it returns ``None``,
  we try the next one in the chain (if any).
  If it raises :exc:`~dmr.exceptions.NotAuthenticatedError`
  then we immediately stop and return the error response.
  Async auth has async ``__call__``, sync auth has sync one.
- :meth:`~dmr.security.SyncAuth.security_schemes`
  provides OpenAPI spec to define this auth method in the spec.
- :meth:`~dmr.security.SyncAuth.security_requirement`
  provides OpenAPI spec to indicate what kind of auth will
  be required for each endpoint using this auth.

Some classes provide configuration to be adjusted when creating instances.
For example: :class:`~dmr.security.jwt.auth.HeaderJWTSyncAuth`
contains multiple options in its ``__init__`` method.

There are 4 ways to provide auth classes for an endpoint:

.. tabs::

  .. tab:: per endpoint

    .. literalinclude:: /examples/auth/per_endpoint.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per controller

    .. literalinclude:: /examples/auth/per_controller.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per settings

    Set :data:`~dmr.settings.Settings.auth` setting
    to enable auth for all controllers.

    .. code-block:: python
      :caption: settings.py
      :linenos:

      >>> from dmr.settings import Settings, DMR_SETTINGS
      >>> from dmr.security.django_session import DjangoSessionSyncAuth

      >>> DMR_SETTINGS = {Settings.auth: [DjangoSessionSyncAuth()]}

    When your project mixes sync and async endpoints,
    use :class:`~dmr.security.SyncOrAsyncAuth` in settings:

    .. code-block:: python
      :caption: settings.py

      >>> from dmr.settings import Settings
      >>> from dmr.security import SyncOrAsyncAuth
      >>> from dmr.security.http import HttpBasicAsyncAuth, HttpBasicSyncAuth

      >>> DMR_SETTINGS = {
      ...     Settings.auth: [
      ...         SyncOrAsyncAuth(
      ...             HttpBasicSyncAuth(),
      ...             HttpBasicAsyncAuth(),
      ...         ),
      ...     ],
      ... }

    .. note::

      :class:`~dmr.security.SyncOrAsyncAuth` is only allowed
      in ``DMR_SETTINGS``. Using it on a controller or endpoint
      raises :exc:`~dmr.exceptions.EndpointMetadataError`.

Providing several auth instances means that at least one of them must succeed.


Disabling auth
~~~~~~~~~~~~~~

It is a common practice to define a global auth protocol
in settings and then disable auth per specific endpoints
like ``/registration`` and ``/login``.

To do so, set ``auth=None`` for the specific
endpoints / controllers that should not have auth.

Setting ``None`` as ``auth`` in any place will always disable
all auth in further layers.

.. note::

  We don't allow setting ``Settings.auth`` to ``None``,
  because it will globally disable all auth with no ways to re-enable it.


.. _auth-www-authenticate:

``WWW-Authenticate`` challenges
-------------------------------

.. versionadded:: 0.15.0

`RFC 9110 <https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.2>`_
says that a ``401`` response must tell the client how to authenticate:

  The server generating a 401 response MUST send a ``WWW-Authenticate``
  header field containing at least one challenge
  applicable to the target resource.

So, we add that header to every ``401`` that
:exc:`~dmr.exceptions.NotAuthenticatedError` produces.
It does not matter where the error came from: the auth chain running out
of options, an auth instance rejecting the credentials,
or your own endpoint raising it by hand.

With :class:`~dmr.security.http.HttpBasicSyncAuth` enabled, a ``401`` looks
like this:

.. code-block:: http

  HTTP/1.1 401 Unauthorized
  Content-Type: application/json
  WWW-Authenticate: Basic realm="api", charset="UTF-8"

A challenge is a scheme name followed by its auth params. Here ``Basic``
is the scheme, and it carries two params:

- ``realm`` names the protection space the credentials are for.
  `RFC 7617 <https://www.rfc-editor.org/rfc/rfc7617.html#section-2>`_
  requires it for the ``Basic`` scheme. Change it with ``realm=``.
- ``charset`` tells the client which encoding to use for the
  username and password. ``UTF-8`` is its only allowed value, and it
  matches what we decode the credentials as, so we always send it.
  See `RFC 7617 <https://www.rfc-editor.org/rfc/rfc7617.html#section-2.1>`_.

When an endpoint has several auth instances, we join their challenges
into a single header value, because
`RFC 9110 <https://www.rfc-editor.org/rfc/rfc9110.html#section-11.6.1>`_
allows a challenge list:

.. code-block:: text

  WWW-Authenticate: Basic realm="api", charset="UTF-8", Bearer

.. note::

  Both auth params and challenges are comma-separated, so such a list
  is ambiguous to parse on its own. Clients resolve it by looking for
  a token with no ``=`` in it - ``Bearer`` above starts a new challenge,
  while ``charset="UTF-8"`` is another param of ``Basic``.


What is supported
~~~~~~~~~~~~~~~~~

A challenge can only name an HTTP authentication scheme that the client
is supposed to send in the ``Authorization`` header.
Auth that reads credentials from a cookie or from a custom header
has nothing to put there, so it sends no challenge at all:

.. list-table::
  :header-rows: 1
  :widths: 45 30 25

  * - Auth
    - Challenge
    - Configurable
  * - :class:`~dmr.security.http.HttpBasicSyncAuth`,
      :class:`~dmr.security.http.HttpBasicAsyncAuth`
    - ``Basic realm="api", charset="UTF-8"``
    - ``realm=``
  * - :class:`~dmr.security.jwt.auth.HeaderJWTSyncAuth`,
      :class:`~dmr.security.jwt.auth.HeaderJWTAsyncAuth`
    - ``Bearer``
    - ``auth_scheme=``
  * - :class:`~dmr.security.token.HeaderTokenSyncAuth`,
      :class:`~dmr.security.token.HeaderTokenAsyncAuth`
    - ``Token``, when a ``prefix=`` is set
    - ``prefix=``
  * - :class:`~dmr.security.jwt.cookie.CookieJWTSyncAuth`,
      :class:`~dmr.security.jwt.cookie.CookieJWTAsyncAuth`
    - none, the token lives in a cookie
    - \-
  * - :class:`~dmr.security.token.CookieTokenSyncAuth`,
      :class:`~dmr.security.token.CookieTokenAsyncAuth`
    - none, the token lives in a cookie
    - \-
  * - :class:`~dmr.security.django_session.auth.DjangoSessionSyncAuth`,
      :class:`~dmr.security.django_session.auth.DjangoSessionAsyncAuth`
    - none, the session lives in a cookie
    - \-
  * - :class:`~dmr.security.allauth.auth.XSessionTokenSyncAuth`,
      :class:`~dmr.security.allauth.auth.XSessionTokenAsyncAuth`
    - none, ``X-Session-Token`` is not an auth scheme
    - \-

The header-based classes only send a challenge when they actually read
the ``Authorization`` header. Point them at a header of your own, and the
challenge goes away, because there is no way to ask a client
for ``X-Api-Auth`` in a standard challenge:

.. code-block:: python

  >>> from dmr.security.jwt import HeaderJWTSyncAuth

  >>> HeaderJWTSyncAuth().www_authenticate_challenge
  'Bearer'

  >>> HeaderJWTSyncAuth(auth_header='X-Api-Auth').www_authenticate_challenge

The same applies to :class:`~dmr.security.token.HeaderTokenSyncAuth`,
which defaults to a prefix-less ``X-API-Token`` header:
without a scheme prefix there is no scheme name to build a challenge from.


Disabling it
~~~~~~~~~~~~

Pass ``www_authenticate=False`` to any auth that supports a challenge:

.. code-block:: python

  >>> from dmr.security.jwt import HeaderJWTSyncAuth

  >>> HeaderJWTSyncAuth(www_authenticate=False).www_authenticate_challenge

.. warning::

  Browsers show their own native login prompt when they see a ``Basic``
  challenge on a ``401``. If your API is called from a browser and you do
  not want that popup, turn the challenge off for HTTP Basic auth.

.. note::

  We only add this header to
  :exc:`~dmr.exceptions.NotAuthenticatedError` responses.
  If you build a ``401`` yourself with :exc:`~dmr.response.APIError`,
  pass the header yourself via its ``headers=`` argument.

The header is added by :func:`~dmr.errors.global_error_handler`,
so replacing that handler is how you change or drop this behavior
for the whole project.


.. _auth-views-security:

Security of auth views
----------------------

Views that issue or accept credentials get extra protection out of the box.
All the auth views we ship already do all of the below,
you only need this when you write your own auth views.


Never cache credentials
~~~~~~~~~~~~~~~~~~~~~~~

Every response that carries credentials
must set the ``Cache-Control: no-store`` header,
so it is never written to any shared or local cache.

Use :data:`~dmr.security.NO_STORE_HEADERS` for that,
it also documents the header in the OpenAPI schema:

.. code:: python

  @modify(headers=NO_STORE_HEADERS)

.. note::

  Only the successful response gets this header,
  because only it carries credentials.
  Error responses of auth views are not affected.


Keep credentials out of error reports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Django hides sensitive data from tracebacks
that are shown to admins in error reporting middlewares:

1. :func:`django.views.decorators.debug.sensitive_post_parameters`
   hides the request's ``POST`` data.
   Apply it with :func:`~dmr.decorators.endpoint_decorator`
2. :func:`django.views.decorators.debug.sensitive_variables`
   hides local variables of a single function

.. code:: python

  >>> from django.views.decorators.debug import (
  ...     sensitive_post_parameters,
  ...     sensitive_variables,
  ... )

  >>> from dmr import Body, Controller, modify
  >>> from dmr.decorators import endpoint_decorator
  >>> from dmr.plugins.pydantic import PydanticSerializer
  >>> from dmr.security import NO_STORE_HEADERS

  >>> class MyLoginController(Controller[PydanticSerializer]):
  ...     @sensitive_variables()
  ...     @endpoint_decorator(sensitive_post_parameters())
  ...     @modify(headers=NO_STORE_HEADERS)
  ...     def post(self, parsed_body: Body[dict[str, str]]) -> str:
  ...         return self.login(parsed_body)
  ...
  ...     def login(self, parsed_body: dict[str, str]) -> str:
  ...         return 'Logged in!'

.. warning::

  ``@sensitive_variables()`` must be the topmost decorator,
  otherwise the wrappers below it will still show
  the parsed request body in the traceback.

.. note::

  Django protects sync and async functions differently.

  A sync ``@sensitive_variables()`` also hides local variables
  of everything the decorated function calls,
  which is why ``login`` above needs no decorator of its own.

  Async functions do not have a shared call stack,
  so every coroutine that keeps credentials in its local variables
  needs its own decorator. This includes your own overrides,
  like ``convert_auth_payload``, which receives the raw password.


Permissions
-----------

Many similar frameworks also include different abstractions
for defining permissions classes, like:
``guards=[UserHasPermissions('delete')]`` or ``IsSuperUser()``, etc.

We don't do that on purpose.
This is not a framework logic, this is your business logic.
It should be placed inside your code, not ours.

Making proper abstractions inside your own code base will allow you to:

- Make it super specific for your usecase
- Make it optimized
- Make it clean and consistent with other business rules you will have

Yes, these permissions can look cool in a framework on paper,
but they do not serve a good purpose in large codebases in reality.

Focus on your **domain**, not on framework.


Next up
-------

Select auth backend that fits your needs:

.. grid:: 1 1 2 2
    :class-row: surface
    :padding: 0
    :gutter: 2

    .. grid-item-card:: HTTP Basic
      :link: http-basic
      :link-type: doc

      Support for HTTP's default basic auth.

    .. grid-item-card:: Django Session
      :link: django-session
      :link-type: doc

      Support for Django's default auth mechanism.

    .. grid-item-card:: JWT Tokens
      :link: jwt
      :link-type: doc

      Support for JWT tokens based auth.

    .. grid-item-card:: Opaque Tokens
      :link: token
      :link-type: doc

      Database-backed opaque token auth with revocation support.

    .. grid-item-card:: Your own auth
      :link: custom
      :link-type: doc

      Write an auth class for a transport we don't ship.


JWT vs Opaque Tokens
~~~~~~~~~~~~~~~~~~~~

Both are valid token-based auth strategies.
The right pick mostly comes down to how you feel
about revocation vs a database lookup on every request.

.. list-table::
  :header-rows: 1
  :widths: 20 40 40

  * -
    - JWT
    - Opaque Token
  * - Storage
    - Stateless, no database lookup
    - Row in the database, looked up per request
  * - Revocation
    - Hard: valid until expiry,
      needs a blocklist to revoke early
    - Easy: ``revoked_at`` is set, token is dead instantly
  * - Token size
    - Larger, carries claims in the payload
    - Small, just a random string
  * - Per-request cost
    - Signature verification, no I/O
    - One DB read per request, plus an optional write
      if last-use tracking is enabled
  * - Good fit for
    - High-throughput / distributed services
      where a DB round-trip per request is too costly
    - APIs that need instant logout,
      audit trails, or per-token metadata

If you need instant revocation or per-token state
(last used, scopes, device info), use :doc:`Opaque Tokens <token>`.
If you need to skip a database lookup on every request
and can tolerate tokens staying valid until they expire,
use :doc:`JWT <jwt>`.


API Reference
-------------

.. autoclass:: dmr.security.SyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.AsyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.SyncOrAsyncAuth
  :members:

.. autofunction:: dmr.security.request_auth

.. autofunction:: dmr.security.add_www_authenticate

.. autodata:: dmr.security.NO_STORE_HEADERS


.. autoclass:: dmr.security.AuthenticatedHttpRequest
  :members:
