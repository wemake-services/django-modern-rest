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
  More on that :ref:`later <swapping-token-model>`.


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

    When in doubt, use this as the default way to receive tokens.

    Use :class:`~dmr.security.token.HeaderTokenSyncAuth` and
    :class:`~dmr.security.token.HeaderTokenAsyncAuth`
    for header-based auth.

    You can customize:

    - Security scheme name, default: ``token``
    - Header name, default: ``X-API-Token``
    - Header value prefix, default: ``''``
    - :meth:`Advanced token parameters <dmr.security.token.token.TokenLikeSync.issue>`

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

    You can customize:

    - Security scheme name, default: ``token``
    - Cookie name, default: ``token``
    - :meth:`Advanced token parameters <dmr.security.token.token.TokenLikeSync.issue>`

    .. literalinclude:: /examples/auth/token/using_token_cookie.py
      :caption: views.py
      :linenos:
      :language: python

Customizing auth
~~~~~~~~~~~~~~~~

Token Auth supports a lot of customization options:
starting from ``token_size`` up to the secret key customization.

See :meth:`~dmr.security.token.token.TokenLikeSync.issue`
for more info on all configuration options.


Token lifecycle
---------------

.. important::

  Token text itself can only be obtained once.
  This is an important security limitation by design.
  Why? Because we never store the token text itself, we only store its hash.

.. mermaid::
  :caption: Default token model states
  :config: {"theme": "forest"}

  stateDiagram-v2
      [*] --> Active: TokenLike.issue / TokenLike.aissue
      Active --> Revoked: TokenLike.revoke / TokenLike.arevoke
      Active --> Expired

All token instances are issued and revoked in sync mode
via :class:`dmr.security.token.token.TokenLikeSync`
and in async mode via
:class:`dmr.security.token.token.TokenLikeAsync` interfaces.

Our default implementation :class:`dmr.security.token.app.models.Token`
strictly follows both interfaces.

Issuing a token
~~~~~~~~~~~~~~~

To issue a token one can use two main strategies:

1. Manually call:

   - :meth:`~dmr.security.token.token.TokenLikeSync.issue`
   - :meth:`~dmr.security.token.token.TokenLikeAsync.aissue`

   methods and copy the token.
   This might be useful if you only want to have just a couple of clients.

2. Provide an API view for users to obtain tokens when they need them.
   To do so, we provide two :ref:`reusable-controllers`:

   - :class:`~dmr.security.token.views.ObtainTokenSyncController`
   - :class:`~dmr.security.token.views.ObtainTokenAsyncController`

To use a pre-defined controller, you will need to:

1. Provide actual types for serializer, request model, and response body.
   Optionally you can also provide a ``User`` model type
   as the 4th type argument, by default it is ``AbstractBaseUser``
2. Redefine
   :meth:`~dmr.security.token.views.ObtainTokenSyncController.convert_auth_payload`
   to convert your request model into the kwargs
   of :func:`django.contrib.auth.authenticate` to authenticate your request
3. Redefine
   :meth:`~dmr.security.token.views.ObtainTokenSyncController.make_api_response`
   to return the response in the format of your choice

.. literalinclude:: /examples/auth/token/token_obtain.py
  :caption: views.py
  :linenos:
  :language: python

In this example we utilize pre-defined types of request model and response body,
only doing the bare minimum with no customizations.

Things that you can customize:

- Request body format
- Response body format
- Token settings, like ``expiration``, ``algorithm``, ``salt``, and ``secret``
- Token class itself
- Error messages, see :ref:`customizing-error-messages`
- Error handling, see :doc:`../error-handling`
- Response status code and any other regular controller or endpoint features

Revoking a token
~~~~~~~~~~~~~~~~

Tokens can be revoked via helper methods:

- :meth:`~dmr.security.token.token.TokenLikeSync.revoke`
- :meth:`~dmr.security.token.token.TokenLikeAsync.arevoke`

Here's an example with the default model:

.. literalinclude:: /examples/auth/token/revoke_token.py
  :caption: revoke_token.py
  :linenos:
  :language: python

.. _cleaning-up-old-tokens:

Cleaning up old tokens
~~~~~~~~~~~~~~~~~~~~~~

Auth finds a token by its hash and then checks
:attr:`~dmr.security.token.app.models.Token.is_active`.
Expired and revoked tokens always fail that check,
so deleting their rows changes nothing for the client:
a ``401`` stays a ``401``, it just says "unknown token" now.

Which means:

- Rows that are still active must stay,
  including the ones with ``expires_at`` set to ``None``,
  because such tokens never expire
- Rows with ``expires_at`` in the past
  and rows with ``revoked_at`` set can be removed,
  they can never authenticate anyone again

Deleting a token is not a replacement for revoking it,
:meth:`~dmr.security.token.token.TokenLikeSync.revoke` is what stops
a token that is still active. Cleanup is just housekeeping afterwards,
and it is worth doing periodically:

.. literalinclude:: /examples/auth/token/token_cleanup.py
  :caption: myapp/management/commands/cleanup_tokens.py
  :linenos:
  :language: python

Note that ``expires_at__lt`` never matches ``NULL``,
so tokens without an expiry date are safe from this query by construction.

Then run this task as a periodic job.

.. note::

  Keep a grace period that matches your auditing needs.
  Dead rows still tell you when a token was issued, last used, and revoked,
  which is the kind of thing you want during an incident.
  For the same reason you might want to archive them
  somewhere else instead of just deleting them.

  If you :ref:`swapped the token model <swapping-token-model>`,
  adjust the query to the fields your own model has.

.. tip::

  Blocklisted JWT tokens have the same problem and the same solution,
  see :ref:`cleaning-up-blocklisted-tokens`.


Django admin
------------

When ``'dmr.security.token.app'`` is in ``INSTALLED_APPS``,
default :class:`~dmr.security.token.app.models.Token` model entries
are accessible from the Django admin for viewing, searching, filtering,
and revocation.

.. note::

  Token creation is intentionally disabled in the admin.
  :func:`~dmr.security.token.token.TokenLikeSync.issue` returns the raw
  token exactly once and an admin form has no way to surface
  that value. Use :func:`~dmr.security.token.token.TokenLikeSync.issue`
  or :func:`~dmr.security.token.token.TokenLikeAsync.aissue`
  directly to issue tokens instead.

Active tokens can be revoked individually from the change form,
or in bulk using the **Revoke selected tokens** action from the
change list.


Tracking last use
-----------------

Auth classes accept an ``update_last_used`` flag for tracking
when a token was last successfully used. It is opt-in,
defaulting to ``False``:

.. code-block:: python

  >>> from dmr.security.token import HeaderTokenSyncAuth

  >>> HeaderTokenSyncAuth(update_last_used=True)
  <dmr.security.token.auth.header.HeaderTokenSyncAuth object at ...>

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

.. warning::

  Token's ``last_used_at`` is not updated atomically.
  If you need a transaction, you should override ``authenticate`` method
  and wrap it in ``transaction.atomic()``,
  but it would make the process even slower.


Customizing the User model
--------------------------

Our :class:`~dmr.security.token.app.models.Token` model
links to the ``User`` type
via customizable setting value:

.. code-block:: python

  models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dmr_tokens')

So, if you configure your ``settings.AUTH_USER_MODEL``
to be something else than the default user
(but, still a subclass of :class:`django.contrib.auth.models.AbstractBaseUser`),
it would just work out of the box.


.. _swapping-token-model:

Swapping the token model
------------------------

.. note::

  Swapping the model is an advanced feature,
  using the default :class:`~dmr.security.token.app.models.Token` model
  is the correct way in most cases.

Let's say that you already have some token auth mechanism
from `some other API framework <https://github.com/encode/django-rest-framework/blob/main/rest_framework/authtoken/models.py>`_
with existing ``CustomToken`` model that you want to continue using,
so nothing would change for your users.

This old model might have a completely different structure,
different fields, user models, etc.
What we care about is that you implement:

- :class:`~dmr.security.token.token.TokenLikeSync` interface for sync auth
- :class:`~dmr.security.token.token.TokenLikeAsync` interface for async auth
- Both of them, if you need a model that works with sync and async auth,
  like our default :class:`~dmr.security.token.app.models.Token` does

.. note::

  Custom token models can support custom user models as well.
  Our interfaces are even generic on the ``User`` type,
  see :ref:`custom-user-token-model` below.

  Otherwise, you would be required to work with
  :class:`~django.contrib.auth.models.AbstractBaseUser`
  which is :pep:`the default type parameter <696>`
  for ``TokenLikeSync`` and ``TokenLikeAsync``.

Here's an example of a custom model with sync interface only:

.. literalinclude:: ../../../django_test_app/server/apps/token_auth/models.py
  :caption: models.py
  :language: python
  :linenos:

Next, let's define an auth class with a different model type:

.. literalinclude:: ../../../django_test_app/server/apps/token_auth/auth.py
  :caption: auth.py
  :language: python
  :linenos:

And protect your views with this new auth type:

.. literalinclude:: ../../../django_test_app/server/apps/token_auth/views/example.py
  :caption: views.py
  :language: python
  :linenos:

This way you can keep old tokens and old model for your existing users.
API stability is important!

.. note::

  This way you can also have different auth classes
  that work with different models types,
  if this is a business requirement you have.

.. _custom-user-token-model:

Using a custom user model
~~~~~~~~~~~~~~~~~~~~~~~~~

``TokenLikeSync`` and ``TokenLikeAsync`` are generic on the ``User`` type,
so a custom token model can point at any
:class:`~django.contrib.auth.models.AbstractBaseUser` subclass,
not just the default ``User`` model or basic ``AbstractBaseUser``:

.. literalinclude:: ../../../django_test_app/server/apps/token_custom_user/models/user.py
  :caption: models/user.py
  :language: python
  :linenos:

Parametrize both interfaces with it to get a model
that works with sync and async auth at the same time:

.. literalinclude:: ../../../django_test_app/server/apps/token_custom_user/models/token.py
  :caption: models/token.py
  :language: python
  :linenos:
  :end-at: # Interfaces implementation

The auth classes then declare the custom model,
and the exact user type variable is inferred from it:

.. literalinclude:: ../../../django_test_app/server/apps/token_custom_user/auth.py
  :caption: auth.py
  :language: python
  :linenos:

Which is all that is needed to protect both sync and async views:

.. literalinclude:: ../../../django_test_app/server/apps/token_custom_user/views.py
  :caption: views.py
  :language: python
  :linenos:

.. seealso::

  - https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication
  - https://django-ninja.dev/guides/authentication/?h=#api-key


API Reference
-------------

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
