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
      because they will show up in access logs.

    You can customize:

    - Security scheme name, default: ``token``
    - Query parameter name, default: ``token``

    .. literalinclude:: /examples/auth/token/using_token_query.py
      :caption: views.py
      :linenos:
      :language: python


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

TODO

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

  >>> from dmr.security.token.token import HeaderTokenSyncAuth

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
  Our interfaces are even generic on the ``User`` type.

  If you want to customize the ``User`` object that you are working with,
  just inherit from a generic version, like so:

  .. code:: python

      >>> from django.db import models
      >>> from django.contrib.auth.models import User as CustomUser
      >>> from dmr.security.token.token import TokenLikeSync

      >>> class YourToken(TokenLikeSync[CustomUser], models.Model):
      ...     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
      ...
      ...     class Meta:  # Just needed for the doctest example
      ...         app_label = 'token_auth'

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

.. literalinclude:: ../../../django_test_app/server/apps/token_auth/views.py
  :caption: views.py
  :language: python
  :linenos:

This way you can keep old tokens and old model for your existing users.
API stability is important!

.. note::

  This way you can also have different auth classes
  that work with different models types,
  if this is a business requirement you have.

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

Default app
~~~~~~~~~~~

.. autoclass:: dmr.security.token.app.models.Token
  :members:
