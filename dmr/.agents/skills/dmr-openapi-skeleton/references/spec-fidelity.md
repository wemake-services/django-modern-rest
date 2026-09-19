# Spec Fidelity

Use this reference when the user wants generated django-modern-rest code to stay close to an existing OpenAPI source document without turning the scaffold task into a literal schema-reimplementation exercise.

## Non-Negotiable Comparison Pass

When both the source spec and the built schema are available:

- compare top-level metadata
- compare exact public paths
- compare methods by `operationId`
- compare request and response media types
- compare response codes and whether they have bodies
- compare response headers
- compare security schemes and per-operation security requirements
- compare component schema names only when they materially change request and response DTO contracts

Do not stop at “the app runs”. If the schema drifts, either fix the generated code or call out the unsupported area explicitly.

## Fidelity Gate

Use this gate as the default completion policy for source-driven generation.

Blocking mismatches:

- source path shape changed without user approval
- source method missing on a path
- source request or response media type missing
- source response status missing
- source response headers missing
- source security schemes or operation-level security missing
- source top-level metadata missing (`info`, `externalDocs`, `servers`, `tags`)
- docs endpoints do not open in the generated skeleton

Conditionally acceptable mismatches:

- serializer cosmetic differences that do not change the contract, such as extra `title` keys, and only when explicitly disclosed
- internal component-layout differences that do not change request and response DTO contracts

Do not install extra validation libraries just to enforce this gate. Use schema inspection and smoke testing first.

If any blocking mismatch remains, continue iterating or request explicit user approval for each unresolved item.

## Lessons from Real Drift

These are real failure modes that must be guarded against:

- Source `application/xml` and `application/x-www-form-urlencoded` media types were silently collapsed to JSON.
- Source `securitySchemes` and per-operation `security` were dropped entirely.
- Source `info`, `externalDocs`, `servers`, and top-level `tags` were replaced by dmr defaults.
- Public paths were rewritten with `/api/`, trailing slashes, and kebab-case segments even though the source contract did not ask for that.
- Empty `200` responses were changed into JSON `null` bodies.
- Source response headers such as `X-Rate-Limit` and `X-Expires-After` were lost.
- Source reusable schemas like `Address` and `Customer` disappeared from components even though the public operations still worked.
- dmr semantic responses like `406` and `422` appeared in the generated schema even though they were absent in the source document.

## Preserve Top-Level Metadata

If the source spec is authoritative, map its top-level metadata into `OpenAPIConfig` rather than accepting dmr defaults.

Preserve:

- `info.title`
- `info.version`
- `info.summary`
- `info.description`
- `info.termsOfService`
- `info.contact`
- `info.license`
- `externalDocs`
- `servers`
- `tags`

Use a dedicated config helper when the project has one, for example `openapi/config.py`.

## Preserve Public Paths

Treat source paths as the public contract.

- Do not prepend `/api/` unless the user explicitly wants it.
- Do not add trailing slashes unless the user explicitly wants Django-style public URLs.
- Do not rewrite camelCase segments like `/findByStatus` into `/find-by-status/` unless the user explicitly requests path normalization.

Internal Python naming can be idiomatic. Public URL shapes must match the source contract unless the user approves a change.

## Preserve Negotiation and Content Types

Serializer choice does not preserve content negotiation by itself.

When the source spec includes multiple media types:

- generate explicit parsers and renderers for those content types
- keep response contracts scoped to the right content types
- use built-in form-urlencoded support when possible
- keep binary or octet-stream bodies explicit
- for media types with no built-in support and no existing project implementation, choose one of two scaffold modes with the user: `minimal-working` or `strict-stub`

For XML, use the local negotiation examples as the pattern source:

- `docs/examples/negotiation/negotiation.py`
- `docs/examples/negotiation/per_controller.py`
- `django_test_app/server/apps/negotiations/views.py`

If you cannot faithfully support a media type, say so explicitly. Do not silently remove it from the schema.

## Stub Unsupported Media Types

Unsupported media types must use explicit placeholders rather than invented protocol logic.

- Ask the user to choose one mode:
- `minimal-working`: create very small passthrough parser and renderer placeholders so generated endpoints remain callable via curl and docs flows, while keeping TODO comments.
- `strict-stub`: create `Parser` and `Renderer` placeholders whose `parse()` and `render()` raise `NotImplementedError`.
- In both modes, declare the exact `content_type`, avoid speculative protocol implementation, and state that real codec logic is user-owned.
- Still wire placeholders into endpoint `parsers` and `renderers` so OpenAPI contract visibility is preserved.
- Mandatory prompt to ask once per generation when the first unsupported media type is found:
- `Unsupported media type "<media_type>" is not implemented in this project. Choose scaffold mode: "minimal-working" (callable TODO placeholder) or "strict-stub" (NotImplementedError stub).`

This keeps scaffolding honest: contract preserved, runtime behavior intentionally incomplete.

## Completion Summary Format

At the end of source-driven generation, summarize parity in two groups:

- `preserved contract`: source contract elements that match closely enough for a useful scaffold
- `requires user approval`: unresolved drift items

Do not mark the task complete while blocking drift remains unapproved.

## Preserve Empty-Body Semantics

If the source response has no body, do not document a JSON `null` body unless the user accepts that drift.

Use:

- `@modify(status_code=HTTPStatus.NO_CONTENT)` with `-> None` for true no-body responses
- `ResponseSpec(None, status_code=...)` for validated `HttpResponse` endpoints when needed

Also review dmr semantic responses:

- if they would add undocumented `406` or `422` responses, disable them with `DMR_SETTINGS = {Settings.semantic_responses: False}` when fidelity matters

## Preserve Response Headers

If the source response documents headers, reflect them in `ResponseSpec(..., headers={...})`.

This matters for contracts like rate limits, expirations, redirects, and tokens.

## Preserve Security Contracts

If the source spec declares `securitySchemes` or operation-level `security`, keep them in the generated schema even when runtime auth is only a placeholder.

Preferred approach:

- generate auth classes that expose `security_scheme`
- generate matching `security_requirement`
- keep the runtime implementation minimal with a `TODO` if the user only wants a scaffold

This keeps the OpenAPI contract while avoiding fake business logic.

## Preserve Source Components

Do not chase literal parity for every source component if the public request and response DTOs are already preserved.

Prefer to keep extra source components only when they matter to generated request and response contracts or when the user explicitly asks for fuller parity.

This is especially important for:

- externally referenced support schemas
- XML-specific schema metadata
- enums and examples that should survive code generation

## Prefer DMR Errors

Generated skeletons should use DMR error models by default.

- prefer `dmr.errors.ErrorModel` for documented error shapes
- prefer `APIError` and built-in DMR error formatting over custom error DTO boilerplate
- preserve a custom source error schema only when the user explicitly asks for it
