# Version history

We follow [Semantic Versions](https://semver.org/).


## WIP

### Features

- *Breaking*: Renamed `schema_only` parameter to `skip_validation`
- Added `dmr.routing.build_500_handler` handler, #661
- Added support for `__dmr_split_commas__` in `Headers` component, #659
- Added support for native Django urls to be rendered in the OpenAPI,
  now OpenAPI parameters will be generated even without `Path` component, #659
- Do not allow `'\x00'` as `SSEvent.id`, #667

### Bugfixes

- Fixes how `SSEResponseSpec.headers['Connection']` header is specified, #654
- Fixed an `operation_id` generation bug, #652
- Fixed a bug with parameter schemas were registered with no uses in the OpenAPI
- Fixed a bug, when request to a missing page with wrong `Accept` header
  was raising an error. Now it returns 406 as it should, #656
- Fixed fake examples generation, #638
- Fixed OpenAPI schema for custom JWT auth parameters, #660

### Misc

- Improved components and auth docs


## Version 0.1.0 (2026-03-13)

- Initial release
