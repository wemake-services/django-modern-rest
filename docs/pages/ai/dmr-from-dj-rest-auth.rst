dj-rest-auth migration
======================

By example, you can use agent skill
`dmr-from-dj-rest-auth <https://github.com/wemake-services/django-modern-rest/tree/master/.agents/skills/dmr-from-dj-rest-auth>`_
when you already have an existing ``dj-rest-auth`` installation
and want to migrate it to ``django-modern-rest``.

.. important::

  LLM-generated migrations cannot guarantee strict behavioral parity.
  Always review and validate migrated auth flows, cookie flags, CSRF
  behavior, token lifetimes, email verification enforcement,
  and error semantics before production use.

  Auth is the part of your system where a silent regression is most
  expensive. Treat the agent's output as a draft for human review.

.. warning::

  This migration is **not** a drop-in backend swap.

  ``dj-rest-auth`` is a Django REST Framework layer on top of
  ``django-allauth``. We do not reimplement account management:
  ``django-allauth`` keeps owning registration, email verification,
  password reset, social login, MFA, and passkeys through its
  `headless <https://docs.allauth.org/en/latest/headless/index.html>`_ mode,
  while ``django-modern-rest`` owns your own API surface
  and the auth classes that read allauth's credentials.

  That means endpoint paths and payloads change,
  and every API client must be updated.
  Plan it as a coordinated frontend and backend migration.


How to use in Codex
-------------------

1. Point Codex to your auth URL wiring, ``REST_AUTH`` settings,
   any overridden serializers, and the test suite.
2. Ask Codex to use the skill ``$dmr-from-dj-rest-auth``.
3. Migrate one flow at a time and run project CI after each one.

You can use prompt like this:

.. code-block:: text

   $dmr-from-dj-rest-auth Migrate `apps/accounts/` from dj-rest-auth to
   django-modern-rest with django-allauth headless. Keep the same flows,
   the same permissions, and the same security posture: cookie flags,
   CSRF behavior, and whether the current password is required.
   List every path and payload change as approved drift, re-attach the
   side effects of our custom RegisterSerializer, migrate flow-by-flow,
   and run the repository test commands after each flow.

How to use in Claude Code
-------------------------

1. Install the plugin:

.. code-block:: text

   /plugin install github.com/wemake-services/django-modern-rest

2. Verify skills are available:

.. code-block:: text

   /skills list

3. Invoke the skill:

.. code-block:: text

   /skills dmr-from-dj-rest-auth

4. Then describe migration scope and constraints in a normal prompt.


What is migrated
----------------

- ``dj_rest_auth`` login, logout, password change, and password reset views
  to ``django-allauth`` headless endpoints
- ``dj_rest_auth.registration`` and ``dj_rest_auth.mfa`` to their
  ``django-allauth`` headless equivalents
- Social login views to allauth's provider endpoints
- ``rest_user_details``, which allauth does not serve, to your own
  :class:`~dmr.controller.Controller` with typed DTOs
- DRF authentication classes to :doc:`../auth/common` auth classes
- ``REST_AUTH`` settings, which become code rather than configuration
- ``simplejwt`` verify and refresh views to
  :class:`~dmr.security.jwt.views.VerifyTokenSyncController` and
  :class:`~dmr.security.jwt.views.RefreshTokenSyncController`

Account business logic stays in ``django-allauth`` by design.


What needs human attention
--------------------------

The skill reports these explicitly, and they are worth reading carefully:

- **Security posture changes.** Cookie flags, CSRF behavior, token
  lifetime, and whether a token is readable by JavaScript.
  The skill reports these separately from ordinary drift.
- **Custom serializer side effects.** Projects hide provisioning, invites,
  billing, and audit records inside overridden serializers.
  These do not move automatically and must be re-attached
  to an allauth adapter or signal.
- **Client updates.** Every approved path or payload change
  is a change your frontend has to make too.
