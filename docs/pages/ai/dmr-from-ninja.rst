Django Ninja migration
======================

By example, you can use agent skill
`dmr-from-django-ninja <https://github.com/wemake-services/django-modern-rest/tree/master/.agents/skills/dmr-from-django-ninja>`_
when you already have an existing ``django-ninja`` or ``ninja-extra`` API
and want to migrate transport layer to ``django-modern-rest``.

.. important::

  LLM-generated migrations cannot guarantee strict behavioral parity.
  Always review and validate migrated routes, schemas, status codes, headers,
  authentication, throttling, and error semantics before production use.

  This workflow is best used for incremental transport migration:
  controllers, DTOs, routers, URL wiring, and migration-focused tests.


How to use in Codex
-------------------

1. Point Codex to existing API entrypoints, URL wiring, and test suite.
2. Ask Codex to use the skill ``$dmr-from-django-ninja``.
3. Migrate one endpoint group at a time and run project CI after each slice.

You can use prompt like this:

.. code-block:: text

   $dmr-from-django-ninja Migrate `apps/api/` from django-ninja to
   django-modern-rest with strict transport parity. Preserve paths, methods,
   request and response DTOs, auth and throttle behavior, status codes, and
   headers. Keep business logic untouched, migrate slice-by-slice, and run the
   repository test commands after each slice.

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

   /skills dmr-from-django-ninja

4. Then describe migration scope and constraints in a normal prompt.


What is migrated
----------------

- Ninja root wiring and URL setup to DMR router + Django URL includes
- ``@api_controller`` / ``@http_*`` handlers to
  :class:`~dmr.controller.Controller` and
  :class:`~dmr.controller.Blueprint`
- ``ninja.Schema`` models to typed request and response DTOs
- Auth and throttling behavior with project-native integrations
- Migration reporting with:
  ``preserved behavior``, ``approved drift``, ``unresolved gaps``

Business logic is intentionally left unchanged by default.
