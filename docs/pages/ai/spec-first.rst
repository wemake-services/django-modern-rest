Spec-first generation
=====================

By example, you can use agent skill
`dmr-openapi-skeleton <https://github.com/wemake-services/django-modern-rest/tree/master/.agents/skills/dmr-openapi-skeleton>`_
when you already have an OpenAPI contract and want a runnable
``django-modern-rest`` skeleton.

.. important::

  LLM-generated code cannot guarantee strict compliance
  with your OpenAPI specification.
  Always review and validate generated routes, schemas, media types,
  status codes, headers, and security requirements before production use.

  This workflow is best used to save time on generating a project skeleton:
  DTOs, transport handlers, routers, docs wiring, and smoke tests.


How to use in Codex
-------------------

1. Prepare an OpenAPI ``3.1+`` spec (file path, URL, or pasted text).
2. Ask Codex to use the skill ``$dmr-openapi-skeleton``.
3. Review generated transport layer and replace placeholders with real logic.

You can use prompt like this:

.. code-block:: text

   $dmr-openapi-skeleton Read `openapi.yaml` and create a new runnable Django
   project in this folder. Use `django-modern-rest` as your REST framework.
   Bootstrap the environment with `uv`, generate
   `pyproject.toml`, settings, `manage.py`, DTOs, controllers, routers,
   docs wiring, and minimal smoke tests.
   Use `PydanticSerializer`, include `msgspec` and `openapi` extras,
   and do not implement any business logic.

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

   /skills dmr-openapi-skeleton

4. Then provide the OpenAPI source (file path, URL, or pasted spec) and generation constraints.


What is generated
-----------------

- Typed DTOs / serializers
- :class:`~dmr.controller.Controller` / :class:`~dmr.controller.Blueprint`
  objects as operations handlers
- All required ``urls.py`` + project URL wiring
- OpenAPI docs (JSON, ReDoc, Swagger, Scalar)
- Minimal smoke tests

Business logic is intentionally left unimplemented.
