# Version history

We will follow [Semantic Versions](https://semver.org/) since `1.0.0` release.
While in `Development Status :: 3 - Alpha` - we will break
all the things without any notices.

After `Development Status :: 4 - Beta` we will still break things
but with a deprecation period.

What is a public API for us (all criteria must be met)?

1. Things that have public names
2. Things that live in public modules
3. Things that don't live in `internal/` or `compiled/`
4. Things that are explicitly documented in the docs

Later on we will make the API more stable and decrease the amount
of requirements for an API to count as public.

## 0.15.0 WIP

### Breaking changes

- Removed `QueryTokenSyncAuth` and `QueryTokenAsyncAuth` auth classes,
  because they were insecure, you can use [older existing versions](https://github.com/wemake-services/django-modern-rest/blob/14884b432ee075ec3d78ff388944ebc5f0b5d432/dmr/security/token/auth/header.py), #1288
- Removed `FileResponseSpec.file_body`,
  use `FileResponseSpec.return_type` instead, #1278
- Removed `FileMetadataComponent.schema_metadata`,
  now we use `SupportsFileParsing.schema_metadata` instead, #1278
- `SSEvent` does not check `id` and `event` fields for null bytes
  and line breaks on creation anymore, this is now a part of the events
  validation pipeline, so it respects `validate_events`, #1329
- `check_event_field` now raises `ValidationError` instead of `ValueError`,
  so a wrong field is streamed as an `error` event
  and does not break the whole stream, #1329
- `401` responses now carry a `WWW-Authenticate` header as required
  by RFC 9110, when the endpoint's auth can express a challenge.
  Note that browsers show their native login prompt on a `Basic` challenge,
  pass `www_authenticate=False` to the auth instance to opt out, #1334
- `SyncAuth` and `AsyncAuth` now have an abstract
  `www_authenticate_challenge` property, so custom auth classes
  must say what challenge they send, or return `None`
  when they cannot be expressed as one, #1334
- Removed init-only `leeway` argument of `JWToken`,
  it is only used by `JWToken.decode` now, #1324
- `JWToken` does not validate `exp` and `iat` on creation anymore,
  now `JWToken.encode` validates them instead, #1324
- Throttling cache keys are now hashed to keep their length bounded, #1337
- HTTP Basic Auth credentials are no longer URL-decoded,
  so percent-encoded characters such as `%40` are preserved as-is, #1363
- `HttpBasicSyncAuth` and `HttpBasicAsyncAuth` now require
  the `auth_scheme` header prefix, it is `Basic` by default
  and is matched exactly, credentials sent without it
  are not accepted anymore.
  Pass `auth_scheme=''` to keep reading prefixless
  credentials like the older versions did, #1330
- `HttpBasicSyncAuth` and `HttpBasicAsyncAuth` now raise
  `NotAuthenticatedError` when credentials have the right
  `auth_scheme` prefix, but cannot be decoded,
  previously the next auth in the chain was tried, #1330

### Features

- Added `exclude_validate_responses` setting, controller attribute,
  and `@modify` / `@validate` argument to skip response validation
  for the given status codes, like `500`, #1370
- Added `WWW-Authenticate` support for auth classes that read
  the `Authorization` header: `HttpBasicSyncAuth`, `HttpBasicAsyncAuth`,
  `HeaderJWTSyncAuth`, `HeaderJWTAsyncAuth`, `HeaderTokenSyncAuth`,
  and `HeaderTokenAsyncAuth`. Cookie-based and custom-header auth
  send no challenge, because there is none to express.
  Configurable via the new `www_authenticate=` and `realm=` arguments
  and the `SyncAuth.www_authenticate_challenge` property, #1334
- Added `dmr.security.add_www_authenticate` function to add
  the `WWW-Authenticate` header to a `NotAuthenticatedError`.
  `global_error_handler` calls it, so replacing that handler
  is how you change or drop this behavior, #1334
- Added `CookieJWTSyncAuth` and `CookieJWTAsyncAuth`
  to read JWT tokens from cookies instead of headers, #1193
- Added `HeaderJWTSyncAuth` and `HeaderJWTAsyncAuth`,
  `JWTSyncAuth` and `JWTAsyncAuth` are kept as their aliases, #1193
- Added `XSessionTokenSyncAuth` and `XSessionTokenAsyncAuth`
  to authenticate `django-allauth` headless session tokens,
  you would need to install
  [`django-allauth`](https://github.com/pennersr/django-allauth)
  separately, #1193
- Added `query` method support for `PathItem` OpenAPI 3.2.0 spec, #1300
- Added `Parser.validate` method for import-time validation of parser
  configuration, #1304
- Added `Renderer.validate` method for import-time validation of renderer
  configuration, #1306
- Added `Router.ignore_from_spec` to exclude entire router subtrees
  from the generated OpenAPI specification, #1309
- Added `FileMetadata` conditional types, #1278
- Added `SupportsFileParsing.schema_metadata` method to customize
  file schema from the parser, #1278
- Added `validate_event_fields` to the `SSEStreamingValidator` pipeline,
  it checks `id` and `event` fields of all event types,
  including custom ones, #1329
- Added `JWToken.validate_issued_claims` method to customize
  the checks we run before signing a token, #1324
- Added `security.NO_STORE_HEADERS`, all auth views we ship now
  return the `Cache-Control: no-store` header
  and document it in the OpenAPI schema, #1335

### Bugfixes

- Fixed `@modify` and `@validate` typing: passing async `auth`
  or `throttling` to a sync endpoint
  (and sync ones to an async endpoint) is now a type error,
  `links` is now also accepted by all `@modify` overloads, #1393
- Fixed `EndpointMetadata.validate_responses` being annotated
  as `bool | None`, it is always resolved
  from the settings, the controller, and the endpoint, #1370
- Fixed `responses` of `ObtainTokenSyncController`,
  `ObtainTokenAsyncController`, `DjangoSessionSyncController`,
  and `DjangoSessionAsyncController` being narrowed
  to a fixed-size tuple, subclasses could not change it, #1371
- Added missing `@sensitive_variables` decorator to all auth views,
  so credentials and tokens are hidden
  in error reporting middlewares and logs, #1323
- Parsed request data is no longer stored as a local variable
  of the endpoint's frame, because it was shown
  in error reports of any endpoint, #1323
- JWT auth, refresh, and verify now return `401` instead of `500`
  when the token subject cannot be a value of the user lookup field,
  for example a non-numeric `sub` with the default integer `pk`, #1284
- Fixed `DjangoSessionSyncAuth`, `DjangoSessionAsyncAuth`,
  `CookieTokenSyncAuth`, and `CookieTokenAsyncAuth` to check CSRF only
  when this auth class is actually used and not skipped, #1289
- Allow using lazy translations in many places,
  like `Controller.summary`, `ResponseSpec.description`,
  `HeaderSpec.description`, #1298
- Fixed `Router.include` dropping `tags` and `deprecated` metadata, #1299
- Fixed `PathItem` to support `additionalOperations` field for custom
  HTTP methods (like `PURGE`, `LINK`), #1300
- Fixed a bug when non-file parsers were listed in the response schema
  for file responses, #1278
- Fixed `SimpleRate` throttling reports with redis backends,
  it used to error on missing throttling stats, #1333
- SSE events are not validated at all when `validate_events` is `False`,
  `id` and `event` fields used to be checked even then, #1329
- Custom SSE event types now have their `id` and `event` fields
  validated just like `SSEvent` does, #1329
- Fixed `JWToken.decode` validating `exp` and `iat` twice,
  now `leeway`, `verify_exp`, and `verify_iat` are respected
  and invalid tokens return `401` instead of `500`, #1324
- Fixed the JWT blocklist being silently bypassed by tokens without `jti`,
  `JWTokenBlocklistSyncMixin` and `JWTokenBlocklistAsyncMixin`
  now add `jti` to `require_claims`, so such tokens get `401`.
  Blocklisting them returns `401` as well
  instead of failing with a database `IntegrityError`, #1322
- JWT authentication now rejects refresh tokens when access tokens are expected,
  #1320

### Misc

- Documented that `500` must be described or excluded from validation,
  when running with `validate_responses` enabled, #1370
- Fixes AI docs and plugin install instructions, #1311
- Documented safe use of user-provided redirect targets with `RedirectTo`,
  #1326
- Added `dmr-from-dj-rest-auth` agent skill to migrate `dj-rest-auth`
  installations to `django-modern-rest` and `django-allauth` headless, #1193
- Documented why and how to remove expired `BlocklistedJWToken`
  and `Token` rows on a schedule, #1336
- Added a guide on writing your own auth class
  for transports we don't ship, #1366


## 0.14.0 (2026-08-14)

### Breaking changes

- Refactored public `routing.ExternalURL` into protected `_ExternalURL`,
  use `external_path()` function instead, #1262

### Features

- Added initial `ty` support, #1257
- Added `header_name_server_managed` to `HttpSpec` to restrict server-managed headers
  in responses, #1341
- Added support of reusable controllers with `@validate`, #1259
- Added default value to `prefix` parameter in `Router.__init__`, #1267
- Added `to_urlpatterns` function to include `Router`
  instances into `urlpatterns` or other routers, #1262

### Bugfixes

- `OpenAPIConfig.openapi_version` now support any `str` argument, #1252

### Misc

- Improve reusable controllers docs, #1259


## 0.13.0 (2026-08-10)

This release was focused on better routing and better OpenAPI support.
See https://github.com/wemake-services/django-modern-rest/releases/tag/0.13.0

### Breaking changes

Since this release, we would only publish migration prompts
on the releases page: https://github.com/wemake-services/django-modern-rest/releases

- `Schema.then` is renamed to be `Schema.schema_then`
  to be consistent with other similar names, #1221
- `dmr.openapi.objects.openapi.convert` function is renamed and moved
  to `dmr.openapi.mappers.schema_normalization.dump_schema`, #1221
- `dmr.openapi.objects.openapi.normalize_key`
  and `dmr.openapi.objects.openapi.normalize_value` functions are removed, #1221
- `dmr.openapi.objects.openapi.ConvertedSchema` is renamed and moved
  to `dmr.openapi.mappers.schema_normalization.DumpedSchema`, #1221
- `dmr.openapi.views.base.DumpedSchema` is removed,
  it was just a `str` type alias, #1221
- `dmr.openapi.objects.OpenAPI` is moved
  to `dmr.openapi.openapi.OpenAPI`, #1222
- `rebuild_namespace` parameter in `PydanticSerializer.from_python`
  was renamed to `extra_namespace`, #1222
- Changed `skip_validation` parameter to be kw-only
  on `OpenAPIView.as_view()` and all its subclasses, #1229
- Renamed `dmr.controller.Controller.get_path_item` to
  `get_schema`, so all methods will be consistent, #1238
- Removed `dmr_assert_throttling` and `dmr_assert_async_throttling`
  fixtures from `pytest`, because there was ever no need to make them fixtures,
  use regular functions instead, #1245
- Removed `dmr.test.types` module, because it was only needed
  for `dmr_pytest` throttling fixtures, #1245
- Moved `dmr.test.types.ThrottlingWhen` to `dmr.test.throttling`, #1245

### Features

- Django 6.1 official support, #1214
- Added `--skip-validation` to the `dmr_export_schema` management command, #1225
- Added `extra_namespace` parameter to `BaseSerializer.from_python`
  and all its existing subclasses, #1222
- Added an ability to load external OpenAPI schemas
  into our typed dataclasses, #1222
- Added `external_path()` function, so we can load external views, #1239
- Added `Router.include()` method to include one router into another one, #1244
- Added an option to skip some controllers / endpoints
  from the OpenAPI spec, #1238
- Added `dmr.test.disabled_auth` test helper
  to disable auth to speed up tests, #1216

### Bugfixes

- Fixed a bug that `OpenAPIConfig.components` were silently
  ignored when defined with custom user's data, #1229
- Fixed missing `$ref`, `$anchor`, `$comment`, and `$schema` fields in `Schema`, #1232
- Fixed `OpenAPIFormat.IRI` value, #1228

### Misc

- Improved testing docs, #1216


## 0.12.1 (2026-07-31)

### Bugfixes

- Added missing `@sensitive_post_parameters` decorator
  to all auth views, #1189
- Fixed `@endpoint_decorator` passing incorrect parameters
  to the endpoint function, #1189
- Fixed `@endpoint_decorator` not working properly with async endpoints, #1189


## 0.12.0 (2026-07-30)

### Features

- Added "Opaque Token" auth backend, #1051
- Added `VerifyTokenSyncController` and `VerifyTokenAsyncController`
  reusable controllers to verify JWT access tokens, #1129
- Added test helpers in `dmr.test` for asserting that endpoints are
  throttled, #1167

### Bugfixes

- Streaming with `streaming_ping_seconds` no longer leaves the pending
  ping timer task behind on every produced event, #1046
- Fixed `500` error on request bodies containing invalid `utf-8` bytes
  inside `msgspec`'s json and msgpack parsers,
  now `400` is correctly returned, #1135
- Properly warn users that use our `pytest` plugin,
  but do not have `pytest_django` installed, #1167
- CSRF is now ensured before any other actions in Django-Session auth, #1180,
- Fixed that `jwt` extra was required in `throttling` code, #1178
- Fixed many places that were missing `__slots__`, #1185

### Misc

- Enabled stricter `__slots__` checks in CI, #1183
- Improved `pytest` plugin docs
- Added `nanodjango` and µDjango examples
  to the micro-framework docs page, #1049


## Version 0.11.0 (2026-06-27)

In this release we significantly improved the DX of defining common
auth and throttling types in the settings that could be used
for both sync and async controllers at the same time.

### Breaking changes

- Dropped macOS [x86_64 wheel support](https://github.com/pyca/cryptography/issues/13520)
- Dropped Django 4.2 support

### Features

- Added `SyncOrAsyncThrottle` class to apply a single throttle rule
  to both sync and async endpoints via global settings, #1075
- Added `SyncOrAsyncAuth` class to apply a single auth rule
  to both sync and async endpoints via global settings, #1102

### Bugfixes

- Fixed several compatibility issues on older Django 5.x versions, #1096
- Fixed `LeakyBucket` throttling algorithm corner cases, #1044
- Fixed OpenAPI schema generation for enum values used
  in path, query, header, and cookie parameters, #1059
- Fixed that `dmr.plugins.msgspec.msgpack` cache was not cleared
  on `clear_settings_cache` calls

### Misc

- Renamed the default OpenAPI title from `Django Modern Rest`
  to `Your Awesome Project` and documented all `OpenAPIConfig`
  fields, #1021


## Version 0.10.0 (2026-05-26)

### Breaking changes

- *Breaking*: `FileResponseSpec()` now describes inline file responses
  and does not include `Content-Disposition` by default. Use
  `FileResponseSpec(as_attachment=True)` when returning Django's
  `FileResponse(..., as_attachment=True)`, #1020

### Migrations prompt

User-facing changes:

```md
Change all existing `dmr.files.FileResponseSpec` usages
to include `as_attachment=True` parameter.
```

### Features

- Added support for JSON Schema 2020-12 dynamic reference keywords
  (`$dynamicRef`, `$dynamicAnchor`, `$defs`) in OpenAPI schema generation.
  These can now be propagated through `extra_json_schema`
  for generic type definitions, #1039

### Misc

- Use `typing_extensions.Sentinel` for `dmr.types.EMPTY`, #995
- `pyrefly@1.0` official support, #1015
- `mypy@2.0` and `mypy@2.1` official support, #1013


## Version 0.9.0 (2026-05-07)

### Features

- Added `throttling_allow_unsafe_cache` setting to control whether unsafe
  cache backends (`LocMemCache`, `DummyCache`) are allowed for throttling.
  Emits `UnsafeCacheBackendWarning` by default,
  raises `ImproperlyConfigured` when explicitly set to `False`, #978
- Added `--no-ensure-ascii` flag to `dmr_export_schema` management command

### Bugfixes

- Fixed how `msgspec` generates `null` in `anyOf`,
  it is now always the last item, #990
- Fixed minimum allowed django version, #1008
- Fixed `ImportError` while using with `django==5.2.0`, #1006


## Version 0.8.0 (2026-04-26)

### Breaking changes

- *Breaking*: Renamed `APIRedirectError` to `RedirectTo`, #922
- *Breaking*: Split `BaseThrottleBackend` into `BaseThrottleAsyncBackend`
  and `BaseThrottleSyncBackend`, #942
- *Breaking*: Renamed `DjangoCache` into `SyncDjangoCache`,
  added `AsyncDjangoCache`, #942
- *Breaking*: Changed `BaseThrottleBackend` API: now it requires
  `.incr` and `.get` methods, the first one should ideally
  be an atomic increment, the second one is for reading objects only, #942
- *Breaking*: Removed `BaseThrottleAlgorithm.record` method,
  now `BaseThrottleAlgorithm.access` must also record accesses.
  This will help to make throttling more atomic, #942

### Migrations prompt

User-facing changes:

```md
Apply this change to the code that uses `django-modern-rest`:
1. Replace `dmr.response.APIRedirectError` with `dmr.response.RedirectTo`
2. Replace `dmr.throttling.backend.DjangoCache`
   with `dmr.throttling.backend.SyncDjangoCache` for sync throttles
   and with `dmr.throttling.backend.AsyncDjangoCache` for async throttles
```

### Features

- Added `SyncRedis` and `AsyncRedis` throttling backends, #977
- Added `RefreshTokenSyncController` and `RefreshTokenAsyncController`
  to issue new access/refresh token pairs from a valid refresh token, #907
- Added `validate_negotiation` metadata flag, so we can explicitly validate,
  that returned response followed the negotiation process, #711
- Added `accepted_header` as a faster alternative
  to `django`'s `HttpRequest.accepts`, #854
- Added `dmr_export_schema` management command to export OpenAPI schemas, #909

### Bugfixes

- Fixed OpenAPI schema for Django session auth
  when `CSRF_USE_SESSIONS=True`, #674
- Fixed that `itemSchema` was possible to be rendered
  in OpenAPI `3.0.0` and `3.1.0`, #908
- Fixed response validation when global error handler returns
  `HttpResponse` with a different content type than the negotiated
  renderer, #711
- Fixed `collectstatic` failure when using `ManifestStaticFilesStorage`, #927
- Fixed `datetime` validation when using `.to_response`, #938
- Fixed a bug that `ObtainTokensAsyncController` was not setting
  the `request.auser` attribute, #953
- Fixed a bug that `JWTSyncAuth` was not setting `request.auser`, #953
- Fixed `ResponseNegotiator` raising `NotAcceptableError` on streaming
  endpoints when `Accept: text/event-stream` was sent without
  `application/json` (the default browser `EventSource` case), which
  made 4xx/5xx error bodies and response validation crash with a 500
  instead of rendering the configured non-streaming default, #962
- Fixed that original traceback was not shown
  for `BaseSchemaGenerator.get_schema`, #961

### Misc

- Optimized `dmr_client` and `dmr_rf` test fixtures to use `msgspec`
  for JSON encoding and decoding when available, #889 and #976
- Optimized how per-endpoint throttle locks are used, #942


## Version 0.7.0 (2026-04-14)

### Breaking changes

1. Removed public `OpenAPIView.dumps` customization hook, #847
   If you customized schema output for `OpenAPIJsonView`, subclass
   the concrete view and override `.get()` instead.
   For JSON output, use `dmr.openapi.core.dump.json_dump`
   if you need the framework's default serializer
2. *Breaking*: `get_jwt` is renamed to `request_jwt`, #868
3. *Breaking*: `ResponseSpecProvider.provide_response_specs` is now
   an instance method, #877
4. *Breaking*: new required `router` parameter added
   to `Endpoint.get_schema` and `Controller.get_path_item`, #879

### Migration Prompt

```md
Apply this change to the code that uses `django-modern-rest`:
1. Replace `OpenAPIView.dumps` usage with `dmr.openapi.core.dump.json_dump`
   usage
2. Change `dmr.security.jwt.auth.get_jwt` function
   to use `dmr.security.jwt.auth.request_jwt` instead, if user expects
   to always get a token back, add `strict=True` argument
3. Change `provide_response_specs` class method to be instance method,
   replace all `cls` usage with `self`
4. Add `router: Router` parameter to `Endpoint.get_schema`
   and `Controller.get_path_item` methods
```

### Features

- Added official PyPy 3.11+ support, #870
- Added `dmr.throttling` package, #877
- Added `request.__drm_auth__` on all successful auth workflows, #868
- Added `request_auth` helper function, #868
- Added `AuthenticatedHttpRequest` type for better
  `request: AuthenticatedHttpRequest[User]`
  type annotations in controllers, #888
- Added `strict` parameter to `request_renderer` and `request_parser`,
  added `@overload`s to both of these functions, #869
- Added `ResponseSpecMetadata` type to represent
  headers and cookies with annotations, useful for error models, #882
- Allow individual `OpenAPI` views to skip schema validation, #867
- Added endpoint validator to prevent sync
  and async generator HTTP endpoints, #843
- Added CSP-friendly templates for shipped `OpenAPI` UI views, #847
  `SwaggerView`, `RedocView`, `ScalarView`, and `StoplightView`
  now avoid inline scripts in DMR-managed templates.
  Final CSP compatibility still depends on the upstream renderer bundle.
- Added `tags` and `deprecated` parameters to `Router` for OpenAPI metadata,
  #872. All operations in a router can now be grouped and marked as deprecated.

### Bugfixes

- Fixed that `OpenAPI` was revalidated on every `.convert` call, #867
- Fixed missing `request.auser()` after `JWTAsyncAuth`, #884
- Fixed `ParameterMetadata` missing `__slots__`, #890
- Fixed `SSEvent` missing `__slots__`, #901
- Fixed `SSE` protocol typing, #894
- Fixed a bug when we were treating controllers with
  no `api_endpoints` as non-abstract, #894
- Fixed a bug when you were not able to subclass
  a controller with a serializer, #873

### Misc

- Added `dmr` skill for agents to write better `django-modern-rest` code, #886
- Switched from `Make` to [`just`](https://github.com/casey/just)
  as a command runner


## Version 0.6.0 (2026-04-09)

In this release we significantly increased the performance of `pydantic`
workflows by introducing `PydanticFastSerializer`.

No breaking changes in this release.

### Features

- Added `PydanticFastSerializer` to serialize and deserialize `json`
  objects directly, #830
- Added support for complex `pydantic` fields inside
  `TypedDict`, `@dataclass`, etc models, when using `PydanticSerializer`
  and `msgspec` parsers / renderers, #842
- Introduced official `to_json_kwargs` and `to_model_kwargs` class-level API
  for `msgspec` and `pydantic` serializers, #842
- Added "Problem Details" or RFC-9457 support, #78
- Added customizable `json_module` parameter to `JsonParser` and `JsonRenderer`
  to support alternative JSON backends like `orjson`, #857

### Bugfixes

- Fixed package metadata, #824
- Fixed missing `style`, `phone`, `color` formats from `OpenAPIFormat`, #842
- Fixes Django 5.2.13+ compat in `DMRAsyncRequestFactory`, #853

### Misc

- Improved "Plugins" section in the docs, #835
- Bumped `msgspec` to `0.21.0`, #856
- Added official `SECURITY.md` policy


## Version 0.5.0 (2026-04-05)

AKA "The first compiled version".

This release will focus on better errors, performance, and stability.

No breaking changes in this release.

### Features

- Added `mypyc` support for compiling parts of the framework
  to run significantly faster, for example our compiled content
  negotiation is now 35 times faster then the Django's default one, #202
  See our https://django-modern-rest.readthedocs.io/en/latest/pages/deep-dive/performance.html#mypyc-compilation docs about that
- Added older Django versions `4.2`, `5.0`, `5.1` official support, #803
- Added official `NamedTuple` support, #774
- Added `timezone` and `pydantic-extra-types` dependencies
  with `[pydantic]` extra, #802
- Added `exclude_semantic_responses` options, #786
- Added an option to override `exclude_semantic_responses`
  and `no_validate_http_spec` settings with `None`
- Added a new way to resolve annotations for controllers:
  `AnnotationsContext`, #787
- Added `yaml` view for OpenAPI schema, #745

### Bugfixes

- Fixed `StreamingValidator` swallowing errors
  when `validate_events` was `True`, but no event model was resolved, #780
- Fixed `dataclass` instances serialization with `PydanticSerializer`
  without `msgspec` json renderer, #795
- Fixed missing `password` OpenAPI format, #805
- Fixes incorrect settings validation, #821

### Misc

- Added `QuerySet` tutorial, #792
- Migrated from `poetry` to `uv` for dependency management
- Set up automated secure publishing to PyPI, #823
- Added CodSpeed integration for continuous performance monitoring, #810


## Version 0.4.0 (2026-03-29)

AKA "The first version that I enjoy".

### Breaking changes

1. We changed how components are defined in controllers, #738
   Now components will be defined in method parameters, not in base classes.

2. We removed `dmr.controller.Blueprint`, because it is not needed anymore.
   It was used to compose different classes with different parsing strategies.
   Since, it was only used for different parsing rules

3. We removed `dmr.routing.compose_blueprints` function,
   because there no `Blueprint`s anymore :)

4. We completely changed our SSE and streaming API, see #736
   Old API was removed, new one was introduced.
   `dmr.sse` package was moved to `dmr.streaming.sse`

We always ship AI prompts to all breaking changes.
So, it would be easier for you to migrate
to a newer version using AI tool of your choice.

### Migration Prompt

To migrate `django-modern-rest` to version `0.4.0` and above, you need to:
1. Load the latest documentation from https://django-modern-rest.readthedocs.io/llms-full.txt
2. Convert component parsing from old class-based API to new method-based API.
  Before:

  ```python
  from dmr import Blueprint, Body
  from dmr.routing import compose_blueprints
  from dmr.plugins.pydantic import PydanticSerializer


  class UserCreateBlueprint(
      Body[_UserInput],  # <- needs a request body
      Blueprint[PydanticSerializer],
  ):
      def post(self) -> _UserOutput:
          return _UserOutput(
              uid=uuid.uuid4(),
              email=self.parsed_body.email,
              age=self.parsed_body.age,
          )


  class UserListBlueprint(Blueprint[PydanticSerializer]):
      def get(self) -> list[_UserInput]:
          return [
              _UserInput(email='first@example.org', age=1),
              _UserInput(email='second@example.org', age=2),
          ]


  UsersController = compose_blueprints(UserCreateBlueprint, UserListBlueprint)
  ```

  To:

  ```python
  from dmr import Controller, Body
  from dmr.plugins.pydantic import PydanticSerializer


  class UsersController(Controller[PydanticSerializer]):
      def get(self) -> list[_UserInput]:
          return [
              _UserInput(email='first@example.org', age=1),
              _UserInput(email='second@example.org', age=2),
          ]

      def post(self, parsed_body: Body[_UserInput]) -> _UserOutput:
          return _UserOutput(
              uid=uuid.uuid4(),
              email=self.parsed_body.email,
              age=self.parsed_body.age,
          )
  ```

3. Replace all `Blueprint` and `compose_blueprints` references with a new API:
  Instead you must use `Controller` and different methods under a single class
4. Now, change all `@sse`-based controllers to new `SSEController` API, from:

  ```python
  from collections.abc import AsyncIterator

  import msgspec
  from django.http import HttpRequest

  from dmr.components import Headers
  from dmr.plugins.msgspec import MsgspecSerializer
  from dmr.sse import SSEContext, SSEResponse, SSEvent, sse


  class HeaderModel(msgspec.Struct):
      last_event_id: int | None = msgspec.field(
          default=None,
          name='Last-Event-ID',
      )


  async def produce_user_events(
      request_headers: HeaderModel,
  ) -> AsyncIterator[SSEvent[str]]:
      if request_headers.last_event_id:
          yield SSEvent(f'starting from {request_headers.last_event_id}')
      else:
          yield SSEvent('starting from scratch')


  @sse(MsgspecSerializer, headers=Headers[HeaderModel])
  async def user_events(
      request: HttpRequest,
      context: SSEContext[None, None, HeaderModel],
  ) -> SSEResponse[SSEvent[str]]:
      return SSEResponse(produce_user_events(context.parsed_headers))
  ```

  To:

  ```python
  from collections.abc import AsyncIterator

  import msgspec

  from dmr.components import Headers
  from dmr.plugins.msgspec import MsgspecSerializer
  from dmr.streaming.sse import SSEController, SSEvent


  class HeaderModel(msgspec.Struct):
      last_event_id: int | None = msgspec.field(
          default=None,
          name='Last-Event-ID',
      )


  class UserEventsController(SSEController[MsgspecSerializer]):
      def get(
          self,
          parsed_headers: Headers[HeaderModel],
      ) -> AsyncIterator[SSEvent[str]]:
          return self.produce_user_events(parsed_headers)

      async def produce_user_events(
          self,
          parsed_headers: HeaderModel,
      ) -> AsyncIterator[SSEvent[str]]:
          if parsed_headers.last_event_id is None:
              yield SSEvent('starting from scratch')
          else:
              yield SSEvent(f'starting from {parsed_headers.last_event_id}')
  ```
5. Replace old `dmr.sse` imports with new `dmr.streaming.sse` alternatives

### Features

- Added `@attrs.define` official support, #706
- Added `msgpack` parser and renderer, #630
- Added `JsonLines` or `JsonL` support, #607
- Added `ping` events to `SSE` streaming, #606
- Added `SSE` support for non-`GET` methods, `Body` component parsing, #736
- Added `i18n` support for user-facing error messages
  using Django's `gettext_lazy`, #426
- Added `MediaType` validation for the default `encoding` field
  and OpenAPI 3.2 `itemEncoding` and `prefixEncoding` fields, #695
- Added `MediaTypeMetadata` metadata item to set required parameters
  for the `MediaType` request body
  for `Body` and `FileMetadata` components, #695 and #698
- Added support for Swagger, Redoc, and Scalar CDN configuration, #678
- Added TraceCov integration for API coverage tracking in test suites,
  including automatic request tracking for `dmr_client` and
  `dmr_async_client`, #735.
- Added Stoplight Elements UI for OpenAPI documentation, #748
- Added better `settings` fixture support for `pytest` plugin, #769

### Bugfixes

- Fixed `SSE` controllers `__name__` and `__doc__` generation
  via `@sse` decorator, #700
- Fixed a bug where `FileMetadata` rendered list of schemas incorrectly, #698

### Misc

- Added `$dmr-openapi-skeleton` AI agent skill, #693
- Added `$dmr-from-django-ninja` AI agent skill, #693
- Added `$dmr-from-drf` AI agent skill, #744
- Added ETag usage docs, #699
- Added multiple translations for the user-facing error messages, #718
- Now `MsgspecJsonRenderer` and `JsonRenderer` produce
  the same `json` string in terms of whitespaces, #736


## Version 0.3.0 (2026-03-17)

### Features

- Added `FileResponseSpec` and improved `FileResponse`
  schema generation, #682
- Added `encoding:` support for file media types in `FileMetadata`, #682

### Bugfixes

- Fixed OpenAPI schema for custom HTTP Basic auth headers, #672
- Fixed JWT claim validation and error handling in `JWToken.decode`, #675
- Fixed incorrect OpenAPI schema for `FileResponse`, #682
- Fixed that `404` was not listed in the endpoint's metadata,
  when using `URLRoute` without `Path` component, #685
- Fixed that `404` was not documented in the OpenAPI
  when `Path` component was not used, but `URLPattern` had parameters, #685
- Fixed `ValueError` on operation id generation, #685

### Misc

- Improved "Returning responses" docs, #684


## Version 0.2.0 (2026-03-15)

### Features

- *Breaking*: Renamed `schema_only` parameter to `skip_validation`
- Added `dmr.routing.build_500_handler` handler, #661
- Added support for `__dmr_split_commas__` in `Headers` component, #659
- Added support for native Django urls to be rendered in the OpenAPI,
  now OpenAPI parameters will be generated even without `Path` component, #659
- Do not allow `'\x00'`, `\n`, and `\r`
  as `SSEvent.id` and `SSEvent.event`, #667

### Bugfixes

- Fixes how `SSEResponseSpec.headers['Connection']` header is specified, #654
- Fixed an `operation_id` generation bug, #652
- Fixed a bug with parameter schemas were registered with no uses in the OpenAPI
- Fixed a bug, when request to a missing page with wrong `Accept` header
  was raising an error. Now it returns 406 as it should, #656
- Fixed fake examples generation, #638
- Fixed OpenAPI schema for custom JWT auth parameters, #660
- Fixed `Body` component was not able to properly parse lists
  with `multipart/form-data` parser, #644
- Fixed that not options were passed to `JWToken._build_options`, #671

### Misc

- Improved components and auth docs


## Version 0.1.0 (2026-03-13)

- Initial release
