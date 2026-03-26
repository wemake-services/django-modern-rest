# DRF to dmr mapping

Use this mapping when replacing transport-layer code.

## Core constructs

- `APIView` / `GenericAPIView` -> `Controller[...]` methods
- `ViewSet` / `GenericViewSet` / `ModelViewSet` -> multiple `Controller[...]` handlers + `Router(...)` composition
- `@action(detail=..., methods=[...], url_path=..., url_name=...)` on `ViewSet` -> dedicated DMR controller route preserving detail/list scope, HTTP methods, and route name/path contract
- `@api_view([...])` -> explicit controller methods on routed paths
- DRF router registration (`DefaultRouter`, `SimpleRouter`) -> Django URL wiring + `Router(..., [...])`
- DRF serializer classes (`Serializer`, `ModelSerializer`) -> typed DTO classes used by dmr validation/parsing/rendering
- DRF exception handler hooks -> dmr error handling flow (`handle_error()`, `handle_async_error()`)

## Inputs and outputs

- request body serializer -> `Body[InputDTO]` + `parsed_body`
- query params (`request.query_params`) -> `Query[...]`
- path params (`kwargs`) -> `Path[...]`
- headers/cookies -> `Headers[...]` / `Cookies[...]`
- serializer output -> method return annotation + DTO output model

## Auth, permissions, throttling

- authentication classes -> dmr auth backend wiring
- permission classes (class/action specific) -> dmr auth/permission checks preserving endpoint semantics
- throttle classes -> project-native rate limiting integration via dmr hooks
- `@action` overrides (`permission_classes`, `authentication_classes`, `throttle_classes`, `serializer_class`) -> per-route DMR configuration with action-level parity

## Contract parity reminders

- Keep path and method shape.
- Keep status codes, headers, and error behavior according to selected migration mode.
- Keep pagination/filtering envelope and query semantics.
- Keep parser/renderer behavior for declared media types.
- Keep `204` responses body-less.

## Validation reminders

- Run repository-native linters and tests after each migration slice.
- Prefer existing integration tests as the contract source of truth.
