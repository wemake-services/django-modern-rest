# Version history

We follow [Semantic Versions](https://semver.org/).

## Unreleased

### Bugfixes

- Added `HttpSpec.empty_request_body` validation to prevent using `Body`
  component with HTTP methods that should not have a request body
  (GET, HEAD, DELETE, CONNECT, TRACE).
  Fixes [#246](https://github.com/wemake-services/django-modern-rest/issues/246)
  Use Blueprints to separate methods with different body requirements.

## Version 0.1.0

- Initial release
