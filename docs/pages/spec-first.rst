Spec-first generation
=====================

By example, you can use agent skill
`dmr-llm-spec-first <https://github.com/milssky/dmr-llm-spec-first>`_
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

   $dmr-openapi-skeleton Read openapi.yaml and create a new runnable Django
   project in this folder. Bootstrap the environment with uv, generate
   pyproject.toml, settings, manage.py, DTOs, controllers, routers,
   docs wiring, and minimal smoke tests.
   Use PydanticSerializer, include msgspec and openapi extras,
   and do not implement business logic.


What is generated
-----------------

- typed DTOs / serializers
- ``Controller`` / ``Blueprint`` handlers for operations
- app ``urls.py`` + project URL wiring
- OpenAPI docs endpoints (JSON, ReDoc, Swagger, Scalar)
- minimal smoke tests

Business logic is intentionally left as placeholders.
