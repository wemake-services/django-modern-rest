---
name: dmr-from-drf
description: Migrate an existing Django API from Django REST Framework to django-modern-rest while preserving routes, request/response contracts, auth, permissions, throttling, pagination, and test coverage. Use when replacing APIView/ViewSet/GenericAPIView and DRF serializers/routers with dmr controllers/routers and typed DTOs.
---

# DMR from DRF

## Overview

Migrate `Django REST Framework` transport layer to `django-modern-rest` incrementally.
Keep business logic unchanged unless user explicitly asks.

Required docs (always reference first):
- DMR LLM docs: https://django-modern-rest.readthedocs.io/llms-full.txt
- DRF docs: https://www.django-rest-framework.org
- Local map: [references/drf-to-dmr-map.md](references/drf-to-dmr-map.md)

## Migration Policy

- Default mode: strict transport parity.
- Preserve by default: paths, methods, request/response schemas, status codes, headers, auth semantics, permission semantics, throttling semantics, pagination envelope, filter/query behavior.
- If user approves drift (for example switching to DMR-native error format/status), stop forcing legacy behavior and document this as `approved drift`.
- Never mix implicit drift: every intentional mismatch must be explicitly listed.
- Do not preserve DRF transport internals as implementation strategy.
  Keep observable contracts, but realize them with DMR + project-native libraries.

## Workflow

### 1. Inventory DRF surface

- Read project API entrypoints and URL wiring first.
- Find usages of: `APIView`, `GenericAPIView`, `ViewSet`, `GenericViewSet`, `ModelViewSet`, `@api_view`, DRF routers, DRF serializer classes, parser/renderer classes, auth/permission/throttle classes, DRF exception handler hooks.
- Build per-endpoint migration matrix:
  - path, method, auth, permissions, throttles, parser/renderer behavior,
  - input DTO, output DTO,
  - pagination/filtering contract,
  - expected statuses, expected headers,
  - known error paths.

### 2. Inventory project-native batteries (required)

- Before writing adapters, inspect existing project libraries and integrations
  that should power the migrated transport layer.
- Prefer libraries already used by the project through DMR mechanisms over custom wrappers.
- Examples:
  - auth/rbac integrations,
  - rate limiting packages,
  - pagination and filtering libraries already wired in the repository.

### 3. Freeze observable behavior

- Capture behavior from existing tests + serializers + routing.
- Mark blocking mismatches before coding:
  - route/method changes,
  - schema field changes,
  - auth/permission/throttle changes,
  - pagination/filtering response shape changes,
  - parser/renderer negotiation changes,
  - status/header changes.

### 4. Decide error strategy (required gate)

Choose one and record it before edits:

- `strict parity`:
  - keep existing error status/payload semantics,
  - adapt DMR handlers/context as needed.
- `approved DMR-native errors`:
  - use framework-native error mapping,
  - update tests and docs expectations accordingly,
  - still preserve happy-path behavior and auth/permission/throttle behavior.

### 5. Migrate by slice (app or endpoint group)

- Migrate one bounded slice at a time.
- Keep module layout unless architecture/lint contracts require change.
- Do not keep class names that encode DRF transport internals.
  Rename transport classes to neutral or DMR-oriented names.
- Prefer thin transport adapters:
  - keep usecases/services/repositories untouched,
  - change only DTOs/controllers/router wiring.

### 6. Translate serializers and request/response contracts

- Replace `Serializer` / `ModelSerializer` transport DTO usage with explicit typed DTOs compatible with DMR serializer.
- Map request sources explicitly:
  - body `Body[...]`, query `Query[...]`, path `Path[...]`, headers `Headers[...]`, cookies `Cookies[...]`.
- Split input/output DTOs when response contains server-owned fields.
- Preserve field aliases, required/optional behavior, and validation constraints needed for contract parity.

### 7. Translate DRF handlers to DMR

- Replace function-based `@api_view` endpoints with explicit `Controller[...]` handlers.
- Replace `APIView`/`GenericAPIView`/`ViewSet` actions with DMR controllers and router composition.
- Keep route names and URL shapes stable unless user requested drift.
- Port parser and renderer expectations intentionally.
- Port exception behavior intentionally:
  - strict parity mode: preserve old statuses/payloads,
  - approved drift mode: keep DMR-native errors and update tests.

### 8. Replace API wiring

- Replace DRF router registration and URL wiring with DMR router + Django URL include wiring.
- Keep namespace stability (`api:*` names) unless drift approved.
- Add docs/openapi routes only if project already exposes them or user asks.

### 9. Port auth, permissions, and throttling with native batteries

- Keep auth and permission expectations endpoint-by-endpoint.
- Keep throttling behavior and headers (for example `Retry-After`) unless drift approved.
- Preserve method-specific permission behavior and action-level differences.
- Prefer existing project-native auth/throttle libraries through DMR hooks.
- Always enable global `validate_responses` settings in local development and testing.
- Ensure all extra responses are explicitly declared with `ResponseSpec`.
- Require all responses to pass response validation.
- Avoid DRF compatibility shims as final solution.
  If a temporary shim is unavoidable, mark it explicitly as temporary,
  document replacement plan, and list it in `unresolved gaps`.

### 10. Update tests for DMR tooling

- Replace DRF-specific API test assumptions where necessary with repository-native Django/DMR testing entrypoints.
- Migrate API test fixtures and clients as first-class migration scope:
  keep fixture intent stable (`api_client`, auth fixtures),
  but rebind them to the migrated DMR stack.
- Keep contract assertions endpoint-by-endpoint:
  status codes, payloads, headers, auth/permission behavior, throttle behavior,
  parser/renderer behavior, pagination/filtering semantics.
- Ensure negative-path tests cover declared extra responses and match
  `ResponseSpec` metadata.
- Remove persistent DRF transport imports from fully migrated transport/test modules unless explicitly approved as temporary drift.

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
- Preserve auth, permissions, and throttle semantics even when error payload format drifts.
- Preserve pagination envelope and cursor/page semantics unless drift approved.
- Preserve parser/renderer negotiation or explicitly list approved drift.
- Be explicit about framework constraints (for example DMR-native validation behavior).
- Do not use DRF transport classes in migrated slices unless explicitly approved by the user as temporary.
- Do not keep DRF-bound class names in migrated transport code.

## Reporting Format (required)

At each meaningful checkpoint and at completion, report in 3 sections:

1. `preserved behavior`
2. `approved drift`
3. `unresolved gaps`

`unresolved gaps` must include concrete files/endpoints and why unresolved.

## Migration Pitfalls (DRF-derived)

- DRF routers often default to trailing slash behavior; preserve URL shape exactly.
- `partial=True` update semantics can diverge if required/optional DTO constraints are translated mechanically.
- Pagination response envelopes (`count/next/previous/results` and ordering) must stay stable unless drift approved.
- Content negotiation can change behavior if parser/renderer defaults are not ported intentionally.
- Action-level permissions and throttles in `ViewSet` classes must be preserved per action, not only per class.
- Header-bearing responses (for example location or throttle headers) must be declared and tested explicitly.

## Output Checklist

- DRF root wiring replaced with DMR routing for migrated slices.
- DRF API views/viewsets replaced with DMR controllers.
- DRF transport serializers replaced with DTOs for migrated endpoints.
- Auth/permission/throttle behavior preserved or explicitly drift-approved.
- Pagination/filtering and parser/renderer behavior preserved or explicitly drift-approved.
- Project-native batteries were evaluated first and used where possible.
- No persistent DRF shim or DRF-bound naming remains in migrated transport layer.
- Tests updated only where needed to keep equivalent behavioral coverage for selected strategy.
- Response validation is enabled and all migrated endpoint responses pass it
  (including extra responses declared via `ResponseSpec`).
- Repository-native CI entrypoints executed per slice.
- Final report emitted in required 3-section format.
- After successful migration and green CI for migrated API surfaces, remove `djangorestframework` from project dependencies unless user explicitly approves keeping it.
