---
name: dmr-from-dj-rest-auth
description: Migrate an existing Django auth API from dj-rest-auth to django-modern-rest, moving account flows onto django-allauth headless and rebuilding the transport layer with dmr controllers and auth classes. Use when replacing dj_rest_auth login/logout/registration/password/MFA/social views and their DRF serializers.
---

# DMR from dj-rest-auth

## Overview

Migrate a `dj-rest-auth` installation to `django-modern-rest`.

Required docs (always reference first):
- DMR LLM docs: https://django-modern-rest.readthedocs.io/llms-full.txt
- dj-rest-auth docs: https://dj-rest-auth.readthedocs.io
- allauth headless docs: https://docs.allauth.org/en/latest/headless/index.html
- Local map: [references/dj-rest-auth-to-dmr-map.md](references/dj-rest-auth-to-dmr-map.md)

## Read This First

This migration is **not** shaped like `$dmr-from-drf`.

`dj-rest-auth` is a DRF layer on top of `django-allauth`. We do not
reimplement account management. `django-allauth` keeps owning registration,
email verification, password reset, social login, MFA, and passkeys through
its `headless` mode, and `django-modern-rest` owns your own API surface plus
the auth classes that read allauth's credentials.

Three consequences the user must accept before any code is written:

1. **Endpoint paths change.** allauth headless serves its own
   `/_allauth/{client}/v1/...` routes. Strict path parity is not a goal
   and usually not achievable.
2. **Request and response payloads change.** allauth has its own envelope
   (`status`, `data`, `meta`) and its own error format.
3. **Every API client must be updated.** Treat this as a coordinated
   frontend + backend migration, not a drop-in backend swap.

If the user cannot change clients, stop and say so. A compatibility shim
that re-serves `dj-rest-auth` paths and payloads is possible but is a
long-lived maintenance burden. Do not build one silently.

## Migration Policy

- Default mode: `behavioral parity`, not `transport parity`.
  The same things must be possible; the wire format may differ.
- Preserve by default: which flows exist, who can call them, what
  security properties they have, what lands in the database.
- Every path, payload, or status-code change is `approved drift` and must be
  listed explicitly. Never let a drift pass unlisted just because
  the endpoint "still works".
- Never weaken a security property to make a client's life easier.
  Call it out and let the user decide.

## Workflow

### 1. Inventory the dj-rest-auth surface

- Find `dj_rest_auth` in `INSTALLED_APPS` and its URL includes
  (`dj_rest_auth.urls`, `dj_rest_auth.registration.urls`, `dj_rest_auth.mfa.urls`).
- Record every `REST_AUTH` setting in use, they encode real requirements.
  See the settings table in the local map.
- Record every overridden serializer
  (`LOGIN_SERIALIZER`, `REGISTER_SERIALIZER`, `USER_DETAILS_SERIALIZER`, ...).
  These are where projects hide their custom business rules.
- Record which token strategy is active: DRF `authtoken`, `simplejwt`
  with headers, `simplejwt` with cookies, or session login.
- Record whether `django-allauth` is already installed and configured,
  which it usually is.

### 2. Inventory custom behavior (required gate)

`dj-rest-auth` is often customized by subclassing. Before mapping anything,
list for each overridden serializer or view:
- extra fields accepted or returned,
- extra validation,
- side effects (signals, analytics, provisioning, audit records).

Side effects are the part most likely to be lost silently.
Each one must be re-attached to an allauth signal or to your own controller.

### 3. Decide the target auth transport (required gate)

Pick one and record it. See the auth table in the local map.

- allauth headless session tokens -> `XSessionTokenSyncAuth`
- jwt in `Authorization` header -> `HeaderJWTSyncAuth`
- jwt in cookies -> `CookieJWTSyncAuth`
- opaque DB tokens -> `HeaderTokenSyncAuth` and the `dmr` token app
- Django session cookie -> `DjangoSessionSyncAuth`

Match the existing security posture. A project on `JWT_AUTH_HTTPONLY`
cookies must not be silently moved to header tokens readable by JavaScript.

### 4. Wire allauth headless

- Add `allauth`, `allauth.account`, `allauth.headless` to `INSTALLED_APPS`
  and `allauth.account.middleware.AccountMiddleware` to `MIDDLEWARE`.
- Choose the `app` or `browser` client deliberately:
  `app` uses `X-Session-Token`, `browser` uses session cookies.
- Port `ACCOUNT_*` settings so the account rules
  (email verification, unique email, signup fields) stay the same.
- Expose allauth's endpoints in your OpenAPI schema with `external_path()`,
  allauth publishes its own specification.

### 5. Migrate flow by flow

Migrate one flow at a time, in this order, because later flows depend on
being able to log in:

1. login and session
2. logout
3. user details
4. password change
5. password reset
6. registration and email verification
7. social login
8. MFA and passkeys

For each flow: map the endpoint, port custom validation and side effects,
update the client, update tests, then run the repository's checks.

### 6. Rebuild what allauth does not serve

allauth headless has no user-details endpoint. `rest_user_details` becomes
your own `Controller` over your user model, with typed DTOs.
This is normal, and it is the right place for project-specific profile
fields that never belonged in an auth library.

### 7. Translate serializers into typed DTOs

- `TypedDict` is the default for reusable controllers in this project.
- Split input and output DTOs when the response carries server-owned fields.
- Never return password fields, tokens the client should not see,
  or full user objects where the old serializer returned a subset.
- Apply `@sensitive_post_parameters` to anything accepting credentials.
- Apply `@sensitive_variables()` to every method that holds credentials
  or tokens in its local variables, so they never reach error reports.
  Async methods need it on each coroutine, sync ones also cover their callees.
- Return `NO_STORE_HEADERS` from `dmr.security` in `@modify` for any view
  that issues or accepts credentials.

### 8. Port token issuing

- If tokens were issued as cookies (`JWT_AUTH_COOKIE`), keep them as cookies
  with the same flags: `httponly`, `secure`, `samesite`, and the refresh
  cookie's `path`. Do not downgrade them.
- `dmr` enforces CSRF automatically for cookie-based auth,
  which replaces `JWT_AUTH_COOKIE_USE_CSRF`.
- Declare every issued cookie with `CookieSpec` so response validation
  and the OpenAPI schema stay honest.

### 9. Update tests

- Keep one test per flow asserting the same *outcome*, not the same payload:
  a user exists, a session works, a password no longer authenticates.
- Add negative-path tests for every declared error response.
- Assert cookie flags explicitly when cookies carry credentials.
  A missing `httponly` is a silent security regression that no
  happy-path test will catch.

### 10. Validate with repository-native entrypoints

- Run the same commands CI runs.
- Enable `validate_responses` in development and testing.

### 11. Finish gate

Do not mark a flow done until linters pass, tests pass, the client is
updated, and the report is updated.

## Translation Rules

- Account business logic belongs to allauth. Do not fork it into controllers.
- Your own domain logic belongs in your own controllers, not in auth hooks.
- Do not keep `dj_rest_auth` or DRF imports in migrated modules.
- Do not keep serializer class names that encode DRF transport internals.
- Preserve security properties even when payload format drifts.

## Reporting Format (required)

At each checkpoint and at completion, report in 4 sections:

1. `preserved behavior`
2. `approved drift` (paths, payloads, statuses, client changes)
3. `security posture changes`
4. `unresolved gaps`

`security posture changes` is separate on purpose. It must state explicitly
when cookie flags, CSRF behavior, token lifetime, or token visibility
to JavaScript changed, even if the user already approved it.

## Migration Pitfalls

- `dj-rest-auth` logout has two behaviors depending on `SESSION_LOGIN` and
  token strategy. Verify what the deployment actually does before mapping it.
- `LOGOUT_ON_PASSWORD_CHANGE` silently invalidates sessions.
  allauth's behavior differs; check it rather than assuming.
- `OLD_PASSWORD_FIELD_ENABLED` controls whether the current password is
  required. Turning this off during migration is a security regression.
- Blindly copying `JWT_AUTH_*` settings loses the cookie flags,
  because they become arguments to `NewCookie`, not settings.
- Custom `REGISTER_SERIALIZER` side effects (provisioning, invites, billing)
  disappear unless re-attached to allauth signals.
- `simplejwt` refresh-token rotation and blacklisting are not automatic
  in `dmr`. Use the `dmr` jwt blocklist app if the project relied on it.
- Social login callback URLs are provider-registered. Changing the path
  requires updating provider configuration too.

## Output Checklist

- allauth headless is wired and serving the account flows.
- Auth transport chosen deliberately and matching the previous posture.
- User-details and any project-specific endpoints rebuilt as dmr controllers.
- All serializers replaced with typed DTOs; no `dj_rest_auth` imports remain.
- Cookie flags and CSRF behavior preserved or explicitly drift-approved.
- Custom validation and side effects re-attached and tested.
- allauth endpoints represented in the OpenAPI schema.
- Response validation enabled and passing.
- Clients updated for every approved path or payload change.
- Final report emitted in the required 4-section format.
- After green CI, remove `dj-rest-auth`, and `djangorestframework` if nothing
  else needs it, from project dependencies.
