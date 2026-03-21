# Version history

We follow [Semantic Versions](https://semver.org/).


## WIP

### Features

- Added `@attrs.define` official support, #706
- Added `msgpack` parser and renderer, #630
- Added `MediaType` validation for the default `encoding` field
  and OpenAPI 3.2 `itemEncoding` and `prefixEncoding` fields, #695
- Added `MediaTypeMetadata` metadata item to set required parameters
  for the `MediaType` request body parameters
  for `Body` and `FileMedata` components, #695 and #698
- Added support for Swagger, Redoc, and Scalar CDN configuration, #678

### Bugfixes

- Fixed `SSE` controllers `__name__` and `__doc__` generation, #700
- Fixed a bug where `FileMetadata` rendered list of schemas incorrectly, #698

### Misc

- Added `$dmr-openapi-skeleton` AI agent skill, #693
- Added `$dmr-from-django-ninja` AI agent skill, #693
- Added i18n support for user-facing error messages
  using Django's `gettext_lazy`, #426


## Version 0.3.0 (2026-03-17)

### Features

- Added ``FileResponseSpec`` and improved ``FileResponse``
  schema generation, #682
- Added ``encoding:`` support for file media types in ``FileMetadata``, #682

### Bugfixes

- Fixed OpenAPI schema for custom HTTP Basic auth headers, #672
- Fixed JWT claim validation and error handling in `JWToken.decode`, #675
- Fixed incorrect OpenAPI schema for ``FileResponse``, #682
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
- Fixed ``Body`` component was not able to properly parse lists
  with ``multipart/form-data`` parser, #644
- Fixed that not options were passed to ``JWToken._build_options``, #671

### Misc

- Improved components and auth docs


## Version 0.1.0 (2026-03-13)

- Initial release
