---
name: dmr-from-django-ninja
description: Migrate an existing Django API from django-ninja/ninja-extra to django-modern-rest while preserving routes, request/response contracts, auth, throttling, and test coverage. Use when replacing NinjaExtraAPI/api_controller/http_* handlers/ninja.Schema with dmr controllers/routers and typed DTOs.
---

# DMR from django-ninja

## Overview

Migrate `django-ninja` / `ninja-extra` transport layer to `django-modern-rest` incrementally.
Keep business logic unchanged unless user explicitly asks.

Required docs (always reference first):
- DMR LLM docs: https://django-modern-rest.readthedocs.io/llms-full.txt
- Local map: [references/ninja-to-dmr-map.md](references/ninja-to-dmr-map.md)

## Migration Policy

- Default mode: strict transport parity.
- Preserve by default: paths, methods, request/response schemas, status codes, headers, auth semantics, throttling semantics.
- If user approves drift (for example switching to DMR-native error format/status), stop forcing legacy behavior and document this as `approved drift`.
- Never mix implicit drift: every intentional mismatch must be explicitly listed.
- Do not preserve Ninja infrastructure internals as implementation strategy.
  Keep observable contracts, but realize them with DMR + project-native libraries.

## Workflow

### 1. Inventory Ninja surface

- Read project API entrypoints and URL wiring first.
- Find usages of: `NinjaExtraAPI`, `api_controller`, `http_get/http_post/...`, `ninja.Schema`, `ninja_jwt`, Ninja exception handlers, Ninja throttles.
- Build per-endpoint migration matrix:
  - path, method, auth, throttle, input DTO, output DTO,
  - expected statuses, expected headers,
  - known error paths.

### 2. Inventory project-native batteries (required)

- Before writing adapters, inspect existing project libraries and integrations
  that should power the migrated transport layer.
- Prefer libraries already used by the project ("Django batteries") through DMR
  mechanisms over custom wrappers.
- Examples:
  - rate limiting: prefer `django-ratelimit` integration when it exists,
    instead of wrapping Ninja throttles,
  - auth/account lockout: prefer existing project auth stack (e.g. axes/middleware)
    instead of reusing Ninja-specific auth internals.

### 3. Freeze observable behavior

- Capture behavior from existing tests + DTOs + routing.
- Mark blocking mismatches before coding:
  - route/method changes,
  - schema field changes,
  - auth/throttle changes,
  - status/header changes.

### 4. Decide error strategy (required gate)

Choose one and record it before edits:

- `strict parity`:
  - keep existing error status/payload semantics,
  - adapt DMR handlers/context as needed.
- `approved DMR-native errors`:
  - use framework-native error mapping,
  - update tests and docs expectations accordingly,
  - still preserve happy-path behavior and auth/throttle behavior.

### 5. Migrate by slice (app or endpoint group)

- Migrate one bounded slice at a time.
- Keep module layout unless architecture/lint contracts require change.
- Do not keep class names that encode Ninja infrastructure.
  Rename transport classes to neutral or DMR-oriented names.
- Prefer thin transport adapters:
  - keep usecases/services/repositories untouched,
  - change only DTOs/controllers/router wiring.

### 6. Translate DTOs and components

- Replace `ninja.Schema` with explicit typed DTOs compatible with DMR serializer.
- Map request sources explicitly:
  - body `Body[...]`, query `Query[...]`, path `Path[...]`, headers `Headers[...]`, cookies `Cookies[...]`.
- Split input/output DTOs when response contains server-owned fields.

### 7. Translate handlers to DMR

- Single operation: `Controller[...]`.
- Multi-method path: controllers + composition.
- Keep route names and URL shapes stable unless user requested drift.
- Port exception behavior intentionally:
  - strict parity mode: preserve old statuses/payloads,
  - approved drift mode: keep DMR-native errors and update tests.

### 8. Replace API wiring

- Replace `NinjaExtraAPI` with DMR router + Django URL include wiring.
- Keep namespace stability (`api:*` names) unless drift approved.
- Add docs/openapi routes only if project already exposes them.

### 9. Port auth and throttling with native batteries

- Keep auth expectations endpoint-by-endpoint.
- Keep throttling behavior and headers (e.g. `Retry-After`) unless drift approved.
- Prefer existing project-native auth/throttle libraries through DMR hooks.
- Always enable global `validate_responses` settings in local development and testing.
- Ensure all extra responses are explicitly declared with `ResponseSpec`.
- Require all responses to pass response validation.
- Avoid Ninja compatibility shims as final solution.
  If a temporary shim is unavoidable, mark it explicitly as temporary,
  document replacement plan, and list it in `unresolved gaps`.

### 10. Update tests for DMR tooling

- Replace Ninja-specific test tooling (`ninja.testing.TestClient`,
  NinjaExtra helpers, Ninja URL setup fixtures) with repository-native
  Django/DMR testing entrypoints.
- Migrate API test fixtures and clients as first-class migration scope:
  keep fixture intent stable (`api_client`, `authed_api_client`, token/auth fixtures),
  but rebind them to the migrated DMR stack.
- Audit and update `pytest` plugin wiring (`conftest.py` / plugin modules)
  so migrated API tests no longer depend on Ninja-only fixtures or helpers.
- Keep contract assertions endpoint-by-endpoint:
  status codes, payloads, headers, auth behavior, throttle behavior.
- Ensure negative-path tests cover declared extra responses and match
  `ResponseSpec` metadata.
- Remove persistent `django-ninja` / `ninja-extra` imports from migrated
  test modules unless explicitly approved as temporary drift.

### 11. Validate each slice with repository-native CI entrypoints

- Run the same commands CI uses in this repository.
- Prefer official script entrypoints over ad-hoc command sets.
- If docker-only CI/test environment is required, run in docker.

### 12. Finish gate

Do not mark slice done until:
- linters pass,
- tests pass (or failures are explicitly approved drift),
- report is updated.

## Translation Rules

- Business logic unchanged by default.
- Keep transport deterministic and typed.
- Avoid hidden route normalization changes (trailing slash/prefix).
- Preserve auth and throttle semantics even when error payload format drifts.
- Be explicit about framework constraints (for example DMR-native validation behavior).
- Do not use `django-ninja` / `ninja-extra` classes in migrated slices unless explicitly approved by the user as temporary.
- Do not keep Ninja-bound class names (for example names prefixed with `Ninja...`) in migrated transport code.

## Reporting Format (required)

At each meaningful checkpoint and at completion, report in 3 sections:

1. `preserved behavior`
2. `approved drift`
3. `unresolved gaps`

`unresolved gaps` must include concrete files/endpoints and why unresolved.

## Migration Pitfalls (repo-derived)

- `django-ratelimit` integration: do not pass `method='ALL'` as a string.
  Use `ratelimit.core.ALL` (or equivalent tuple) or rate-limiting silently won't trigger.
- If base Pydantic config uses `strict=True`, JSON UUID strings can fail validation
  (`Input should be an instance of UUID`). For request DTO fields that accept
  UUID from JSON, allow parsing explicitly (for example field-level `strict=False`).
- If preserving strict input schema (unknown fields must fail), do not rely on
  a base model with `extra='ignore'` for input DTOs. Set input DTO config to
  reject extra fields (for example `extra='forbid'`).
- In `approved DMR-native errors` mode, DB integrity failures may surface as
  unhandled 500 if not mapped. Use DMR endpoint/controller error handling
  (`modify(error_handler=...)` or controller-level handler) to keep predictable
  client error behavior without reviving legacy Ninja payload shape.
- CI hygiene: avoid debug commands that create project-local tooling artifacts
  (for example `.local/...` from ad-hoc virtualenv/poetry runs), as format/lint
  stages may scan and fail on them.

## Output Checklist

- Ninja root wiring replaced with DMR routing.
- Ninja controllers/handlers replaced with DMR controllers.
- `ninja.Schema` DTOs replaced for migrated endpoints.
- Auth/throttle behavior preserved or explicitly drift-approved.
- Project-native batteries were evaluated first and used where possible.
- No persistent Ninja shim or Ninja-bound naming remains in migrated transport layer.
- Tests updated only where needed to keep equivalent behavioral coverage for selected strategy.
- Response validation is enabled and all migrated endpoint responses pass it
  (including extra responses declared via `ResponseSpec`).
- Repository-native CI entrypoints executed per slice.
- Final report emitted in required 3-section format.
- After successful migration and green CI for migrated API surfaces, remove 'django-ninja' and 'ninja-extra' from project dependencies unless user explicitly approves keeping them.
