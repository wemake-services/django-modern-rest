---
name: dmr-openapi-skeleton
description: Generate django-modern-rest transport-layer skeletons from OpenAPI 3.1+ specs. Use when Codex needs to turn an OpenAPI file, URL, or pasted document into typed DTOs, controllers or blueprints, routers, Django URL wiring, and minimal tests for this repository or similar projects built on dmr. Trigger on requests to scaffold APIs, bootstrap apps, or map OpenAPI operations to Controller, Blueprint, Router, and OpenAPI view constructs without implementing business logic.
---

# DMR OpenAPI Skeleton

## Overview

Generate runnable transport-layer skeletons for `django-modern-rest` from OpenAPI 3.1+ specifications. Keep the output intentionally thin: produce typed DTOs, base controllers or blueprints, routers, docs wiring, and minimal tests, with zero business logic by default.

Use the repository examples under `django_test_app/server/apps/*` and `tests/*` as the local source of truth. Read [references/framework-patterns.md](references/framework-patterns.md) when choosing dmr constructs, [references/project-map.md](references/project-map.md) when deciding where generated files should live, and [references/spec-fidelity.md](references/spec-fidelity.md) whenever a source OpenAPI document is authoritative and the generated project should preserve the public contract closely enough for a useful boilerplate.

Primary framework documentation:
- https://django-modern-rest.readthedocs.io/llms-full.txt

## Workflow

### 1. Read the specification first

- Read the provided OpenAPI document before editing code.
- Confirm that `openapi` is `3.1.x` or newer. If the document is older, ambiguous, or incomplete, say so before generating files.
- Extract tags, path groups, operation IDs, parameters, request bodies, response codes, reusable schemas, and security declarations.
- Detect difficult constructs early: `oneOf`, `anyOf`, `allOf`, discriminators, multiple media types, callbacks, and webhook sections.

### 1a. Enter spec-fidelity mode when the source spec is authoritative

- If the user provides an existing OpenAPI document and expects the generated project to reproduce it, treat spec fidelity as a first-class requirement.
- Compare the source spec against the built schema after generation whenever both artifacts are available.
- Do not silently normalize paths, drop tags, collapse media types to JSON, or replace source metadata with framework defaults.
- When dmr adds framework-native documentation that is not present in the source spec, either disable it or tell the user explicitly.
- Default objective in this mode is close public-contract parity for a runnable skeleton, not literal identity of every generated component schema.

### 2. Bootstrap the environment when generating a new project

- If the user asks for a new project in a fresh folder, create the environment and dependency manifest, not just source files.
- For a new standalone project, prefer `wemake-django-template` as the project base unless the user explicitly asks for a plain Django skeleton.
- When extending an existing repository or generating only a new app inside a repository, do not try to retrofit `wemake-django-template`.
- Prefer `uv` when the target repository does not already enforce another tool.
- Prefer `poetry` when the target repository already uses `pyproject.toml` with Poetry.
- Fall back to `pip` only when the user explicitly asks for it or the environment is intentionally minimal.
- Install `django-modern-rest` together with the extras needed by the generated code.
- When generating Pydantic-based code, install at least `django-modern-rest[pydantic]`.
- Prefer to include `django-modern-rest[msgspec]` as well, even for Pydantic projects, because local docs recommend `msgspec` for faster JSON parsing and rendering.
- Include `django-modern-rest[jwt]` only when the OpenAPI security model and the user request require JWT support.
- Target Python `3.11+` and Django `5.2+`.
- Do not add `'dmr'` to `INSTALLED_APPS` unless the generated project must serve static files for OpenAPI docs.
- Do not install extra schema-validation libraries just to compare source and built specs. Avoid adding `django-modern-rest[openapi]`, `openapi-spec-validator`, or `schemathesis` unless the repository already has them or the user explicitly asks for them.
- When `wemake-django-template` is used, layer the generated DTOs, controllers, routers, docs wiring, and tests on top of its structure instead of rebuilding the project shell by hand.

### 3. Plan the output shape

- Mirror the nearest existing repository layout instead of inventing a new architecture.
- Prefer one Django app per bounded area, usually by stable tag or first path segment.
- Generate `views.py` and `urls.py` for every app.
- Generate `serializers.py` when an app has reusable request and response DTOs. Keep tiny private helper models inline only when that matches the surrounding code better.
- Generate root `urls.py` OpenAPI docs wiring for every runnable project skeleton.
- Generate minimal tests only for route, schema, and docs smoke coverage unless the user asks for more.

### 4. Choose the serializer deliberately

- Prefer `PydanticSerializer` by default.
- Keep `MsgspecSerializer` only when the repository already standardizes on it or the user explicitly asks for it.
- Fall back to `PydanticSerializer` for complex OpenAPI 3.1 features such as unions, discriminators, aliases, nullability, rich field constraints, or mixed content models.
- If XML or other non-JSON media types are part of the source spec, choose the serializer independently from the parser and renderer strategy. Serializer choice alone does not preserve negotiation.

### 5. Generate DTOs from OpenAPI parts

- Map request bodies to `Body[...]`.
- Map query parameters to `Query[...]`.
- Map path parameters to `Path[...]`.
- Map header parameters to `Headers[...]`.
- Map cookie parameters to `Cookies[...]`.
- Reuse shared schemas across operations instead of duplicating classes.
- Preserve wire-format field names. Introduce aliases only when the schema name is not a valid or readable Python attribute.
- Encode validation constraints from the spec whenever the chosen serializer supports them cleanly.
- Split input and output DTOs when the response adds server-owned fields such as identifiers, timestamps, tokens, URLs, or derived values.
- Preserve reusable schemas when they drive request and response DTOs. Do not optimize for literal full `components.schemas` parity if the public API contract is already preserved.

### 6. Generate views with the correct dmr construct

- Use a direct `Controller[...]` when a route has one operation or when a single class naturally owns the endpoint.
- Use one `Blueprint[...]` per HTTP method and combine them with `compose_blueprints(...)` when the same path exposes multiple operations or materially different request, response, or auth rules.
- Keep one class per operation. Let the router compose them instead of building giant mixed-purpose controllers.
- Name classes from `operationId` when it is stable and explicit. Otherwise derive names from resource plus verb such as `UserListBlueprint`, `UserCreateController`, or `InvoiceRetrieveBlueprint`.

### 7. Generate skeleton behavior, not fake business logic

- Keep runtime handlers transport-only and deterministic.
- Return schema-valid placeholder data, echoed request data, or empty collections.
- Use `@modify(status_code=HTTPStatus.NO_CONTENT)` and `-> None` for `204` or `304` style endpoints.
- Use `self.to_response(...)` only when low-level response construction is actually required.
- Leave short `TODO` comments where persistence, orchestration, auth backends, or external integrations would normally start.
- Never generate domain workflows, service calls, data access logic, pricing rules, permissions rules, or side-effect orchestration unless the user explicitly requests it.
- Do not invent Django models, services, repositories, or nontrivial auth implementations unless the user explicitly requests them.

### 8. Generate routers and project wiring

- Build app routes with `Router([...], prefix='.../')`.
- Use `path(...)` or `re_path(...)` inside the router exactly as local code does.
- Keep trailing slashes in generated routes unless the surrounding project clearly omits them.
- Include app routers from the project root with `include((router.urls, 'app_name'), namespace='...')`.
- Ensure docs are always available for generated runnable skeletons by wiring `build_schema(...)`, `OpenAPIJsonView`, `RedocView`, `SwaggerView`, and `ScalarView`.
- If the source spec is authoritative, preserve its public path contract. Do not add an `/api/` prefix, trailing slash, or kebab-case rewrite unless the user explicitly wants the public API shape changed.

### 9. Generate runnable bootstrap files when requested

- When scaffolding a fresh project, also generate `pyproject.toml` or the package-manager equivalent consistent with the chosen tool.
- Generate `manage.py`, Django settings, root `urls.py`, and app package initializers when they do not exist yet.
- Wire docs endpoints only when the project should expose OpenAPI UIs.
- Add a short run section to the final response with exact commands such as `uv run python manage.py runserver` or `poetry run python manage.py runserver`.

### 10. Generate minimal verification

- Add one smoke test per important route group for status code and response shape.
- Add one OpenAPI smoke test when docs endpoints are generated.
- Add a Schemathesis contract test only when the repository already uses it or the user explicitly asks for it.
- When the source spec is authoritative, compare the generated schema to the source spec before considering the task done. Report drift in paths, media types, response codes, headers, security, tags, servers, and top-level metadata.
- Include a docs-availability smoke check for `openapi`, `redoc`, `swagger`, and `scalar` endpoints in runnable skeletons.
- Do not require external validation tooling for this comparison. Prefer direct schema inspection and smoke tests.

### 11. Apply a practical fidelity gate before finishing

- Treat these as blocking mismatches: missing or changed public path contract, missing source methods, missing primary source media types, missing important source response status codes, missing source response headers when they affect clients, missing source security schemes or operation-level security, missing important top-level metadata (`info`, `externalDocs`, `servers`, `tags`), or docs endpoints not opening.
- Treat internal component-layout differences as non-blocking when request and response DTOs, media types, and public operations remain faithful enough for a usable scaffold.
- Treat serializer-generated cosmetic metadata differences (for example extra schema `title` keys) as acceptable after brief disclosure.
- If blocking mismatches remain, keep iterating or ask the user to approve specific drift with concrete items.
- Do not claim completion until remaining differences are either resolved or explicitly accepted by the user.

## Translation Rules

- Annotate the method return type directly when the handler returns normal Python values that the serializer can render.
- Document additional responses with `ResponseSpec` through `responses = (...)`, `@modify(extra_responses=[...])`, or `@validate(...)`.
- Keep empty-body endpoints compliant with HTTP rules. Do not attach `Body[...]` to methods that normally forbid a request body unless the spec truly requires it and the user accepts explicit `HttpSpec` overrides.
- Reuse existing auth backends when the repository already has them. Otherwise note the declared security requirement with a short `TODO` instead of inventing a backend.
- Prefer simple JSON output first. Generate negotiation-specific parser or renderer code only when the spec truly requires multiple representations or the repository already uses negotiation patterns.
- Keep route names snake_case and stable. Derive them from `operationId` when possible.
- For fresh projects, keep installation commands aligned with local docs:
  `uv add django-modern-rest`,
  `poetry add django-modern-rest`,
  or `pip install django-modern-rest`,
  then extend with extras as needed.
- Preserve top-level source metadata with `OpenAPIConfig`: `title`, `version`, `summary`, `description`, `terms_of_service`, `contact`, `license`, `external_docs`, `servers`, and `tags`.
- If the source spec uses multiple response media types such as `application/json` and `application/xml`, generate matching parsers and renderers or explicitly state that fidelity is partial. Do not silently collapse the contract to JSON-only.
- Use built-in support for `application/x-www-form-urlencoded` when the source spec declares it, and keep `application/octet-stream` or file-style bodies explicit in the generated endpoint contract.
- For media types not supported by the library and not already implemented in the target project, ask the user to pick one scaffold mode:
  `minimal-working` mode: generate minimal passthrough parser and renderer placeholders so endpoints stay callable with curl while still marked as TODO.
  `strict-stub` mode: generate parser and renderer stubs that raise `NotImplementedError`.
- Use this mandatory question template before generating code for the first unsupported media type:
  `Unsupported media type "<media_type>" is not implemented in this project. Choose scaffold mode: "minimal-working" (callable TODO placeholder) or "strict-stub" (NotImplementedError stub).`
- Do not implement full codec logic for unknown media types. Implementation remains user responsibility.
- Use DMR error models by default. Prefer `dmr.errors.ErrorModel`, `APIError`, and related built-in error mechanics over custom source-specific error DTOs unless the user explicitly asks to preserve a custom error schema.
- Preserve documented response headers with `ResponseSpec(..., headers={...})` instead of dropping them.
- Keep dmr semantic responses only when they improve the runnable skeleton and the user accepts the drift. Otherwise disable them with `DMR_SETTINGS = {Settings.semantic_responses: False}`.
- Preserve documented security schemes by generating placeholder auth classes whose `security_scheme` and `security_requirement` expose the source OpenAPI contract, even if the runtime auth logic itself is still a `TODO`.

## Output Checklist

- Create or update the environment manifest when the request is for a fresh project.
- Create schema-valid DTO classes for every request and response model that matters to routing.
- Create `views.py` with typed controllers or blueprints and placeholder implementations.
- Create `urls.py` with `Router` wiring for every generated app.
- Update the project root URLs only when the request is for a runnable project skeleton.
- Add minimal tests or explain why tests were not added.
- If a source spec was provided, confirm whether the built schema preserves paths, top-level metadata, tags, servers, security schemes, response headers, media types, and empty-body semantics.
- Confirm that docs endpoints are available in the generated runnable skeleton.
- For source-driven generation, provide a short fidelity summary split into:
  `preserved contract`,
  `requires user approval`.
