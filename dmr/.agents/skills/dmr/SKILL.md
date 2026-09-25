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

Return models, not Django responses. `HttpResponse` bypasses negotiation,
headers, cookies, and validation. Raise `APIError` for errors,
handle them in `handle_error` / `handle_async_error`, not in the endpoint body:

```python
raise APIError(
    self.format_error('Not found', error_type=ErrorType.user_msg),
    status_code=HTTPStatus.NOT_FOUND,
)
```

Use plain methods by default. Add `@modify(...)` only for a status code,
headers, cookies, auth, throttling, or extra responses that differ
from the inferred ones. Use `@validate(ResponseSpec(...))` only when
the endpoint returns an `HttpResponse` on purpose.

Prefer `MsgspecSerializer`. With `pydantic` and JSON only,
prefer `PydanticFastSerializer` over `PydanticSerializer`.

Use `dmr.routing.path` and `Router`, and install
`build_404_handler` / `build_500_handler` so API errors are JSON.

Keep `validate_responses` on in development and tests, turn it off only
in production settings. Never disable `semantic_responses`,
never set empty `parsers` or `renderers`.

Match sync and async: sync endpoints get sync error handlers and auth,
async endpoints get async ones. Throttle login endpoints before auth.

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
| Typed authenticated requests, throttling, `wrap_middleware` | 3 | [references/security.md](references/security.md) |
| `pytest` style, `DMRClient`, `DMRRequestFactory`, `polyfactory`, `schemathesis` | 5 | [references/testing.md](references/testing.md) |
| Docstrings as OpenAPI descriptions | 1 | [references/openapi.md](references/openapi.md) |

Every rule links to the documentation page that explains it.

## Review checklist

Flag these when reviewing `dmr` code:

- A component parameter with a name other than `parsed_*`.
- `HttpResponse(...)` or `JsonResponse(...)` returned from an endpoint.
- `try` / `except` returning error responses inside an endpoint body.
- `@modify` or `@validate` that changes nothing compared to the defaults.
- `isinstance(exc, APIError)` inside an error handler.
- `validate_responses = False` outside production settings,
  `semantic_responses` disabled, or empty parsers / renderers.
- A sync `handle_error` on an async controller, or the other way around.
- `RemoteAddr(runs_before_auth=False)` on a login endpoint.
- `RedirectTo(next_url)` with a user-provided URL and no
  `url_has_allowed_host_and_scheme` check.
- `django.urls.path` where `dmr.routing.path` is a drop-in replacement.
- `django.test.TestCase`, `RequestFactory`, or `Client`
  where the `dmr_rf` / `dmr_client` fixtures exist.
- Controllers and endpoints without docstrings when OpenAPI is served.
