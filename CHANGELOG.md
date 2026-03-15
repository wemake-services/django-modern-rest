# Version history

We follow [Semantic Versions](https://semver.org/).


## WIP

### Features

- Added `dmr.routing.build_500_handler` handler
- Added support for `__dmr_split_commas__` in `Headers` component
- Added support for native Django urls to be rendered in the OpenAPI,
  now OpenAPI parameters will be generated even without `Path` component

### Bugfixes

- Fixed an `operation_id` generation bug, #652
- Fixed a bug with parameter schemas were registered with no uses in the OpenAPI
- Fixed a bug, when request to a missing page with wrong `Accept` header
  was raising an error. Now it returns 406 as it should, #656

### Misc

- Improved components and auth docs


## Version 0.1.0 (2026-03-13)

- Initial release
