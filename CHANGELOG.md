# Version history

We will follow [Semantic Versions](https://semver.org/) since ``1.0.0`` release.
While in `Development Status :: 3 - Alpha` - we will break
all the things without any notices.

After `Development Status :: 4 - Beta` we will still break things
but with a deprecation period.


## WIP

In this release we significantly increased the performance of `pydantic`
workflows by introducing `PydanticFastSerializer`.

No breaking changes in this release.

### Features

- Added `PydanticFastSerializer` to serialize and deserialize ``json``
  objects directly, #830
- Added support for complex `pydantic` fields inside
  `TypedDict`, `@dataclass`, etc models, when using `PydanticSerializer`
  and `msgspec` parsers / renderers, #842
- Introduced official `to_json_kwargs` and `to_model_kwargs` class-level API
  for `msgspec` and `pydantic` serializers, #842
- Added "Problem Details" or RFC-9457 support, #78

### Fixes

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

### Fixes

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
- Fixed that we were using `typing.get_type_hints` in some places,
  now always using `typing_extensions.get_type_hints`, #768

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
