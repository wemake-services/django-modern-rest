---
name: dmr
description: Write django-modern-rest (dmr) code with the recommended patterns, covering controllers, routers, typed DTOs with msgspec or pydantic, auth, throttling, error handling, OpenAPI, and tests. Use whenever a project depends on django-modern-rest, imports `dmr`, or asks for a typed Django REST API, and when reviewing dmr code for mistakes.
license: MIT
metadata:
  author: wemake-services
  homepage: https://django-modern-rest.readthedocs.io/en/latest/pages/ai/agent-skills.html
---

# django-modern-rest (dmr)

`django-modern-rest` is a typed, sync-and-async REST layer for Django:
`Controller` classes with one method per HTTP verb, DTOs parsed from
`Body`, `Query`, `Headers`, `Cookies`, and `Path` annotations,
`Router` based URLs, built-in auth and throttling,
and OpenAPI generated from the types.

## When to use

- Any file that imports from `dmr`, or a project with
  `django-modern-rest` in its dependencies.
- Requests for a "typed", "modern", or "async" Django REST API.
- Reviews of existing `dmr` code: use the checklist at the end.

For migrations from other frameworks use `dmr-from-drf`,
`dmr-from-django-ninja`, or `dmr-from-dj-rest-auth`.
For version bumps use `dmr-upgrade`.
For scaffolding from an OpenAPI document use `dmr-openapi-skeleton`.

## Workflow

1. **Check the installed version and extras**:
   `uv pip show django-modern-rest` (or the lock file).
   The API changes between minor releases, so read the docs
   for the installed version, not the latest one.
2. **Load the docs you need**, they are versioned and LLM friendly:
   - index: `https://django-modern-rest.readthedocs.io/en/<version>/llms.txt`
   - one page as Markdown: replace `.html` with `.md` in any docs URL,
     for example
     `https://django-modern-rest.readthedocs.io/en/latest/pages/routing.md`
   - everything at once:
     `https://django-modern-rest.readthedocs.io/en/<version>/llms-full.txt`
3. **Read the reference for the area you are changing**
   (see the table below), it holds the full rules with correct and wrong
   examples.
4. **Verify**: run `python manage.py check`, the project's type checker,
   and tests written with the `dmr_client` / `dmr_rf` fixtures.
   For OpenAPI changes, run `python manage.py dmr_export_schema <path>`
   and review the diff.

## Non-negotiable rules

Install `django-modern-rest[msgspec]` even for `pydantic` projects,
it makes JSON parsing fastest. Add `django-stubs[compatible-mypy]`
to dev dependencies, `dmr` relies on Django types.

Name component parameters exactly `parsed_body`, `parsed_query`,
`parsed_headers`, `parsed_path`, and `parsed_cookies`.
Other names are silently not parsed:

```python
class UserController(Controller[MsgspecSerializer]):
    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        return parsed_body
```

Optional components keep `None` inside the annotation:
`parsed_body: Body[UserModel | None] = None`.
`Body[UserModel] | None = None` is an import-time error.

Do not ever use `return HttpResponse(...)`, because it bypasses negotiation,
headers, cookies, and validation.
Instead use `self.to_response(...)` or `self.to_error(...)` in controllers.

Raise `APIError` for errors,
handle them in `handle_error` / `handle_async_error`, not in the endpoint body:

```python
raise APIError(
    self.format_error('Not found', error_type=ErrorType.user_msg),
    status_code=HTTPStatus.NOT_FOUND,
)
```

Prefer `@modify`-styled endpoints to `@validated`-styled endpoints.

Use plain methods by default. Add `@modify(...)` only for a status code,
headers, cookies, auth, throttling, or extra responses that differ
from the inferred ones. Use `@validate(ResponseSpec(...))` only when
the endpoint returns an `HttpResponse` on purpose.

Prefer `MsgspecSerializer`. With `pydantic` and JSON only,
prefer `PydanticFastSerializer` over `PydanticSerializer`.

Prefer `BodyMsgspec` over `Body` when `MsgspecSerializer` is used.

Use `dmr.routing.path` and `Router`, and install
`build_404_handler` / `build_500_handler` so API errors are JSON.

If CSRF and ``csrf_exempt = False`` are used always set
`CSRF_FAILURE_VIEW = build_csrf_handler(router.prefix, ...)`
error handler.

Keep `validate_responses` on in development and tests, turn it off only
in production settings. Never disable `semantic_responses`,
never set empty `parsers` or `renderers`.

Match sync and async: sync endpoints get sync error handlers and auth,
async endpoints get async ones. Throttle login endpoints before auth.

Route auth endpoints from `concrete_views` with `as_view(serializer=...)`,
do not subclass `dmr.security.*.views` controllers
only to restate the default payload and response.
Subclass `views` only when the payload, the response, or a hook differs:

```python
path(
    'auth/',
    concrete_views.ObtainTokensSyncController.as_view(
        serializer=MsgspecSerializer,
    ),
)
```

`as_view` rejects `throttling=`, `auth=`, and other class-only attributes
since `0.17.0`, older versions silently ignore them. Concrete views
use `Settings.throttling`, a login-specific throttle needs a `views` subclass.

Test with `dmr_rf` (`DMRRequestFactory`) for unit tests and `dmr_client`
(`DMRClient`) for full-stack tests, generate payloads with `polyfactory`,
and use `schemathesis` against the OpenAPI schema.

## Quick reference

| Topic | Rules | Read |
| --- | --- | --- |
| Controllers, `@modify` vs `@validate`, serializers, responses, components, redirects | 9 | [references/controllers.md](references/controllers.md) |
| Routing, 404 / 500 handlers, sync and async app layout | 4 | [references/routing.md](references/routing.md) |
| Error handlers, `APIError`, custom `error_model` | 4 | [references/errors.md](references/errors.md) |
| Response validation, `HttpSpec`, settings | 5 | [references/validation.md](references/validation.md) |
| Ready-to-use auth `concrete_views`, typed authenticated requests, throttling, `wrap_middleware` | 4 | [references/security.md](references/security.md) |
| `pytest` style, `DMRClient`, `DMRRequestFactory`, `polyfactory`, `schemathesis` | 5 | [references/testing.md](references/testing.md) |
| Docstrings as OpenAPI descriptions | 1 | [references/openapi.md](references/openapi.md) |

Every rule links to the documentation page that explains it.

## Review checklist

Flag these when reviewing `dmr` code:

- A component parameter with a name other than `parsed_*`.
- `Body[Model] | None = None` instead of `Body[Model | None] = None`.
- `HttpResponse(...)` or `JsonResponse(...)` returned from an endpoint.
- `try` / `except` returning error responses inside an endpoint body.
- `@modify` or `@validate` that changes nothing compared to the defaults.
- `isinstance(exc, APIError)` inside an error handler.
- `validate_responses = False` outside production settings,
  `semantic_responses` disabled, or empty parsers / renderers.
- A sync `handle_error` on an async controller, or the other way around.
- `RemoteAddr(runs_before_auth=False)` on a login endpoint.
- A subclass of an auth controller from `dmr.security.*.views`
  that keeps the default payload and response,
  where its `concrete_views` counterpart does the same.
- Cookie `concrete_views` without `jwt_refresh_cookie_path`,
  so the refresh token is sent with every request.
- `throttling=`, `auth=`, `responses=`, or other class-only attributes
  passed to `as_view()`, including `jwt_expiration=` of cookie controllers:
  they raise since `0.17.0` and are silently ignored before it.
- `RedirectTo(next_url)` with a user-provided URL and no
  `url_has_allowed_host_and_scheme` check.
- `django.urls.path` where `dmr.routing.path` is a drop-in replacement.
- `django.test.TestCase`, `RequestFactory`, or `Client`
  where the `dmr_rf` / `dmr_client` fixtures exist.
- Controllers and endpoints without docstrings when OpenAPI is served.
