# django-ninja to dmr mapping

Use this mapping when replacing transport-layer code.

## Core constructs

- `NinjaExtraAPI(...)` -> Django URL wiring + `Router([...], prefix='...')`
- `@api_controller('/path')` + `ControllerBase` -> `Controller[...]` or per-method `Blueprint[...]`
- `@http_get`, `@http_post`, ... -> regular class methods (`get`, `post`, ...)
- `ninja.Schema` -> serializer DTO classes used by dmr validation/parsing
- `api.exception_handler(...)` -> dmr error flow (`APIError`, `ErrorModel`, response specs)

## Inputs and outputs

- `raw_data: InputDTO` in ninja handlers -> `Body[InputDTO]` mixin + `self.parsed_body`
- plain method args used as query params -> `Query[...]` DTO (or explicit query mapping)
- response model in decorator -> return annotation and optional `ResponseSpec`

## Routing strategy

- One path + one method -> single `Controller` class.
- One path + multiple methods -> one `Blueprint` per method + `compose_blueprints(...)`.
- Keep `url_name` parity by preserving stable route names in Django `path(..., name='...')`.

## Contract parity reminders

- Keep path and method shape.
- Keep auth and throttle expectations.
- Keep status codes and response headers.
- Keep `204` responses body-less.

## Validation reminders

- Run repository-native linters and tests after each migration slice.
- Prefer existing integration tests as the contract source of truth.
