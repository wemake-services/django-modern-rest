# Project Map

Use this repository structure as the default target when the user asks for code generation here.

## Read These Local Examples First

- Read `django_test_app/server/apps/controllers/` for controllers, typed components, and router naming.
- Read `django_test_app/server/apps/models_example/` for a small multi-file app with `serializers.py`, `views.py`, and `urls.py`.
- Read `django_test_app/server/urls.py` for root router inclusion and OpenAPI docs wiring.
- Read `tests/test_integration/test_controllers/` and `tests/test_integration/test_openapi/` for the expected smoke-test style.

## Default File Layout for a Generated App

Generate these files unless the surrounding app already uses a different pattern:

- `<app>/views.py`
- `<app>/urls.py`
- `<app>/serializers.py` for reusable DTOs
- `<app>/__init__.py`

Generate these files only when the request is for a runnable project scaffold:

- project-level `urls.py`
- project-level `settings.py`
- package manifest such as `pyproject.toml` when creating a fresh repository
- `manage.py`
- optional `openapi/config.py` when the user wants explicit docs metadata
- integration tests under `tests/test_integration/`

## Naming and Layout Conventions

- Keep route prefixes and paths trailing-slash based.
- Keep route names snake_case.
- Use `operationId` to derive class names and route names when the spec provides stable values.
- Group operations by tag first, then by stable path prefix when tags are missing or noisy.
- Keep DTOs reusable and transport-focused. Do not merge them with persistence models.
- Keep placeholder logic deterministic enough for smoke tests to pass.

## Default Skeleton Behavior

Use these defaults when the spec does not imply real business logic:

- Keep handlers transport-only: DTO parsing, validation, and response shaping only.
- Echo parsed request bodies for create and update operations when this keeps the endpoint callable without domain logic.
- Return empty lists for collection endpoints unless the response schema requires non-empty data.
- Return placeholder identifiers, timestamps, or URLs only when the response schema requires them.
- Return `None` for `204` endpoints.
- Leave short `TODO` comments for auth adapters, service calls, persistence, and integrations.
- Do not generate any domain business logic by default.

## Environment Defaults

- For a greenfield standalone project, prefer `wemake-django-template` as the base scaffold.
- Fall back to a plain Django skeleton only when the user explicitly asks for it or when you are adding code inside an already-existing repository.
- Prefer `uv` for greenfield scaffolding unless the target repo already uses Poetry.
- Use Poetry when extending a Poetry-managed repo.
- For Pydantic-first OpenAPI generation, prefer dependencies that effectively correspond to `django-modern-rest[pydantic,msgspec]`.
- Add JWT extras only when required.
- Do not add `'dmr'` to `INSTALLED_APPS` unless static OpenAPI assets must be served.
- Do not add extra validation libraries by default just to compare generated and source schemas.
- Keep generated projects on Python `3.11+` and Django `5.2+`.

## Testing Scope

- Prefer narrow integration smoke tests over exhaustive unit tests for generated skeletons.
- Add OpenAPI endpoint coverage only when docs wiring is generated.
- Reuse Schemathesis only when the user asks for contract testing or the target project already includes it.
- For runnable skeletons, ensure docs endpoints (`openapi`, `redoc`, `swagger`, `scalar`) are covered by smoke checks.
