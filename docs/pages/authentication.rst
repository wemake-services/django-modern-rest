Authentication
==============

``django-modern-rest`` supports builtin auth workflows.

We support both:

1. Checking that user requests contains required auth credentials
2. Extra pre-existing boilerplate code to provide tokens for users


Enabling auth
-------------

Let's start with how auth can be enabled and how it works.

There are two main base classes for auth:

1. :class:`~django_modern_rest.security.SyncAuth` for sync controllers
2. :class:`~django_modern_rest.security.AsyncAuth` for async controllers

.. warning::

  Sync controllers can't directly use async auth.
  And async controllers can't directly use sync auth.

All auth - that we are going to use - will be instances for these two classes
(and their subclasses).

All of them have unified API:

- ``__init__`` method contains configuration that can be changed per instance
- :meth:`~django_modern_rest.security.SyncAuth.__call__` does all
  the heavy lifting. If ``__call__`` returns anything but ``None``,
  then we consider auth instance to succeed. If it returns ``None``,
  we try the next one in the chain (if any).
  If it raises :exc:`~django_modern_rest.exceptions.NotAuthenticatedError`
  then we imidiatelly stop and return the error response.
  Async auth has async ``__call__``, sync auth has sync one.
- :meth:`~django_modern_rest.security.SyncAuth.security_scheme`
  provides OpenAPI spec to define this auth method in the spec.
- :meth:`~django_modern_rest.security.SyncAuth.security_requirement`
  provides OpenAPI spec to indicate what kind of auth will
  be required for each endpoint using this auth.

Some class provide configuration to be adjusted when creating instances.
For example: :class:`~django_modern_rest.security.jwt.JWTSyncAuth`
contains multiple options in its ``__init__`` method.

There are 4 ways to provide auth classes for an endpoint:

.. tabs::

    .. tab:: per endpoint

      .. literalinclude:: /examples/auth/per_endpoint.py
        :caption: views.py
        :linenos:
        :language: python

    .. tab:: per blueprint

      .. literalinclude:: /examples/auth/per_blueprint.py
        :caption: views.py
        :linenos:
        :language: python

    .. tab:: per controller

      .. literalinclude:: /examples/auth/per_controller.py
        :caption: views.py
        :linenos:
        :language: python

    .. tab:: per settings

      .. code-block:: python
        :caption: settings.py
        :linenos:

        >>> from django_modern_rest.settings import Settings, DMR_SETTINGS
        >>> from django_modern_rest.security import DjangoSessionSyncAuth

        >>> DMR_SETTINGS = {Settings.auth: [DjangoSessionSyncAuth()]}

Providing several auth instances means that at least one of them must succeed.


Disabling auth
~~~~~~~~~~~~~~

It is a common practice to define a global auth protocol
in settings and then disable auth per specific endpoints
like ``/registration`` and ``/login``.

To do so, set ``auth=None`` for the specific
endpoints / blueprints / controllers that should not have auth.

Setting ``None`` as ``auth`` in any place will always disable
all auth in further layers.

.. note::

  We don't allow setting ``Settings.auth`` to ``None``,
  because it will globally disable all auth with no ways to re-enable it.


Reusing pre-existing views
--------------------------

We provide several pre-existing views to get auth tokens.
So, users won't have to write tons of boilerplate code.


JWT with access and refresh tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We provide two :ref:`reusable-controllers` to obtain
pairs of access and refresh tokens:

1. :class:`~django_modern_rest.security.jwt.views.ObtainTokensSyncController`
   for sync controllers
2. :class:`~django_modern_rest.security.jwt.views.ObtainTokensAsyncController`
   for async controllers

To use them, you will need to:

1. Provide actual types for serializer, request model, and response body
2. Redefine
   :meth:`~django_modern_rest.security.jwt.views.ObtainTokensSyncController.convert_auth_payload`
   to convert your request model into the kwargs
   of :func:`django.contrib.auth.authenticate` to authenticate your request
3. Redefine
   :meth:`~django_modern_rest.security.jwt.views.ObtainTokensSyncController.make_response_payload`
   to return the response in the format of your choice

.. literalinclude:: /examples/auth/jwt_obtain_tokens.py
  :caption: views.py
  :linenos:
  :language: python

In this example we utilize pre-defined types of request model and response body,
only doing the bare minimum with no customizations.

Things that you can customize:

- Request body format
- Response body format
- JWT settings
- Error messages, see :ref:`customizing-error-messages`
- Error handling, see :doc:`error-handling`
- Response status code and any other regular controller or endpoint features

Here's an example with a lot more customizations:

.. literalinclude:: /examples/auth/jwt_complex_tokens.py
  :caption: views.py
  :linenos:
  :language: python

We want to be sure that this class is at the same time:

1. Easy enough to not write a lot of boilerplate code by default
2. Customizable enough to be able to change a lot of stuff that
   can be affected by existing business rules
3. Always type safe


General API Reference
---------------------

.. autoclass:: django_modern_rest.security.SyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.AsyncAuth
  :members:
  :inherited-members:


Django session auth API
-----------------------

.. autoclass:: django_modern_rest.security.DjangoSessionSyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.DjangoSessionAsyncAuth
  :members:
  :inherited-members:


HTTP Basic Auth API
-------------------

.. autoclass:: django_modern_rest.security.http.HttpBasicSyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.http.HttpBasicAsyncAuth
  :members:
  :inherited-members:

.. autofunction:: django_modern_rest.security.http.basic_auth


JWT API
-------

.. important::

  To use ``jwt`` you must install ``'django-modern-rest[jwt]'`` extra.


.. autoclass:: django_modern_rest.security.jwt.JWTToken
  :members:

.. autoclass:: django_modern_rest.security.jwt.JWTSyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.jwt.JWTAsyncAuth
  :members:
  :inherited-members:

Pre-defined views to fetch JWT tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: django_modern_rest.security.jwt.views.ObtainTokensSyncController
  :members: post, login, make_response_payload, create_jwt_token, convert_auth_payload

.. autoclass:: django_modern_rest.security.jwt.views.ObtainTokensAsyncController
  :members: post, login, make_response_payload, create_jwt_token, convert_auth_payload

.. autoclass:: django_modern_rest.security.jwt.views.ObtainTokensPayload
  :members:
  :show-inheritance:

.. autoclass:: django_modern_rest.security.jwt.views.ObtainTokensResponse
  :members:
  :show-inheritance:
