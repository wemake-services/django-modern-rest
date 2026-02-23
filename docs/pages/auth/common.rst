How authentication works
========================

``django-modern-rest`` supports different auth workflows.

We support both:

1. Checking that user requests contains required auth credentials
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

All auth - that we are going to use - will be instances for these two classes
(and their subclasses).

All of them have unified API:

- ``__init__`` method contains configuration that can be changed per instance
- :meth:`~dmr.security.SyncAuth.__call__` does all
  the heavy lifting. If ``__call__`` returns anything but ``None``,
  then we consider auth instance to succeed. If it returns ``None``,
  we try the next one in the chain (if any).
  If it raises :exc:`~dmr.exceptions.NotAuthenticatedError`
  then we imidiatelly stop and return the error response.
  Async auth has async ``__call__``, sync auth has sync one.
- :meth:`~dmr.security.SyncAuth.security_scheme`
  provides OpenAPI spec to define this auth method in the spec.
- :meth:`~dmr.security.SyncAuth.security_requirement`
  provides OpenAPI spec to indicate what kind of auth will
  be required for each endpoint using this auth.

Some class provide configuration to be adjusted when creating instances.
For example: :class:`~dmr.security.jwt.JWTSyncAuth`
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

        >>> from dmr.settings import Settings, DMR_SETTINGS
        >>> from dmr.security.django_session import DjangoSessionSyncAuth

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


Permissions
-----------

Many similar frameworks also include different abstractions
for defining permissions classes, like:
``guards=[UserHasPermissions('delete')]`` or ``IsSuperUser()``, etc.

We don't do that on purpose.
This is not a framework logic, this is your business logic.
It should be placed inside your code, not ours.

Making proper abstractions inside your own code base will allow you to:

- Make is super specific for your usecase
- Make it optimized
- Make it clean and consistent with other business rules you will have

Yes, these permissions can look cool in a framework on paper,
but they do not surve a good purpose in large codebases in reality.

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
