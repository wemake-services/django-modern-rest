<p align="center">
   <a href="https://django-modern-rest.readthedocs.io/">
      <picture>
         <source srcset="https://raw.githubusercontent.com/wemake-services/django-modern-rest/master/docs/_static/images/logo-dark.svg" media="(prefers-color-scheme: dark)">
         <img src="https://raw.githubusercontent.com/wemake-services/django-modern-rest/master/docs/_static/images/logo-light.svg#gh-light-mode-only" alt="Modern REST Logo - Light" width="100%" height="auto" />
      </picture>
   </a>
</p>

<p align="center">
  <em>Modern REST framework for Django with types and async support!</em>
</p>

<div align="center">

[![wemake.services](https://img.shields.io/badge/%20-wemake.services-green.svg?label=%20&logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAABGdBTUEAALGPC%2FxhBQAAAAFzUkdCAK7OHOkAAAAbUExURQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP%2F%2F%2F5TvxDIAAAAIdFJOUwAjRA8xXANAL%2Bv0SAAAADNJREFUGNNjYCAIOJjRBdBFWMkVQeGzcHAwksJnAPPZGOGAASzPzAEHEGVsLExQwE7YswCb7AFZSF3bbAAAAABJRU5ErkJggg%3D%3D)](https://wemake-services.github.io)
[![Modern REST](https://img.shields.io/badge/Modern%20REST-0C4B33?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTA4MCIgaGVpZ2h0PSIxMDgwIiB2aWV3Qm94PSIwIDAgMTA4MCAxMDgwIiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cGF0aCBkPSJNMiA3MDQuMDJMMTQ1LjQ1OSA0NjYuMTlMMjc3Ljg4MyA3MDQuMDJMMTQ1LjQ1OSA5NDEuODQ5TDIgNzA0LjAyWiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTE0NS40NTkgOTQxLjg0OUwyIDcwNC4wMkgyNzcuODgzTDE0NS40NTkgOTQxLjg0OVoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik02NzguOTQ4IDcwNC4wMzVMMzQxLjIzIDEzOEwyMjcuMDcxIDMyOC4yNjRMNDM2LjM2MiA3MDQuMDM1TDMwMy4xNzcgOTQxLjg2NEg1MzYuMjVMNjc4Ljk0OCA3MDQuMDM1WiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTY3OC45MzcgNzA0LjAyNkg0MzYuMzVMMzAzLjE2NiA5NDEuODU2SDUzNi4yMzlMNjc4LjkzNyA3MDQuMDI2WiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTEwNzguMTcgNzA0LjAzNUw3NDAuNDUxIDEzOEw2MjYuMjkzIDMyOC4yNjRMODM1LjU4MyA3MDQuMDM1TDcwMi4zOTkgOTQxLjg2NEg5MzUuNDcyTDEwNzguMTcgNzA0LjAzNVoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik0xMDc4LjE3IDcwNC4wMzVIODM1LjU4M0w3MDIuMzk5IDk0MS44NjRIOTM1LjQ3MkwxMDc4LjE3IDcwNC4wMzVaIiBmaWxsPSJ3aGl0ZSIvPgo8L3N2Zz4K&color=35544A)](https://github.com/wemake-services/django-modern-rest)
[![test](https://github.com/wemake-services/django-modern-rest/actions/workflows/test.yml/badge.svg?event=push)](https://github.com/wemake-services/django-modern-rest/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/wemake-services/django-modern-rest/branch/master/graph/badge.svg)](https://codecov.io/gh/wemake-services/django-modern-rest)
[![No AI slop inside](https://img.shields.io/badge/no-slop-purple.svg)](https://github.com/wemake-services/django-modern-rest/blob/master/.github/AI_POLICY.md)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/django-modern-rest?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BRIGHTGREEN&left_text=downloads)](https://pepy.tech/projects/django-modern-rest)
[![Python Version](https://img.shields.io/pypi/pyversions/django-modern-rest.svg)](https://pypi.org/project/django-modern-rest/)
[![wemake-python-styleguide](https://img.shields.io/badge/style-wemake-000000.svg)](https://github.com/wemake-services/wemake-python-styleguide)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/wemake-services/django-modern-rest)
[![Telegram chat](https://img.shields.io/badge/chat-join-blue.svg?logo=telegram)](https://t.me/django_modern_rest)
</div>

## Features

- [x] [Blazingly fast](https://django-modern-rest.readthedocs.io/en/latest/pages/deep-dive/performance.html)
- [x] Supports `django>=4.2`
- [x] Supports `pydantic2`, `msgspec`, `attrs`, `dataclasses`, `TypedDict` as model schemas, but not bound to any of these libraries
- [x] Supports async Django without any `sync_to_async` calls inside, tested to work with free-threading builds
- [x] Fully typed and checked with `mypy`, `pyright`, and `pyrefly` in strict modes
- [x] Supports content negotiation, has default implementations for `json`, `msgpack`, SSE, Json Lines, and more
- [x] Strict schema validation of both requests and responses, including errors
- [x] Supports OpenAPI 3.1 / 3.2 semantic schema generation out of the box
- [x] Supports all your existing `django` primitives and packages, no custom runtimes
- [x] Great testing tools with [schemathesis](https://github.com/schemathesis/schemathesis), [polyfactory](https://github.com/litestar-org/polyfactory), [tracecov](https://django-modern-rest.readthedocs.io/en/latest/pages/testing.html#api-coverage-with-tracecov), bundled `pytest` plugin, and default Django's testing primitives
- [x] 100% test coverage with 2000+ of carefully designed unit, integration, and property-based tests
- [x] High [security standards](https://github.com/wemake-services/django-modern-rest/blob/master/.github/SECURITY.md)
- [x] Built [by the community](https://github.com/wemake-services/django-modern-rest/graphs/contributors) for the community, not a single-person project
- [x] Great docs
- [x] No AI slop, but [built for the LLM era](https://django-modern-rest.readthedocs.io/en/latest/pages/getting-started.html#llms-support)
- [x] No emojis 🌚️️

---------

<p align="center">
   <a href="https://django-modern-rest.readthedocs.io/en/latest/pages/deep-dive/performance.html">
      <picture>
         <source srcset="https://raw.githubusercontent.com/wemake-services/django-modern-rest/master/docs/_static/images/benchmarks/sync-dark.svg" alt="Benchmark - Dark" width="80%" height="auto" media="(prefers-color-scheme: dark)">
         <img src="https://raw.githubusercontent.com/wemake-services/django-modern-rest/master/docs/_static/images/benchmarks/sync-light.svg#gh-light-mode-only" alt="Benchmark - Light" width="80%" height="auto" />
      </picture>
   </a>

   <em>Sync mode</em>
</p>


## Testimonials

> The one thing I really love about **django-modern-rest** is its pluggable
> serializers and validators. Frameworks that are tightly coupled
> with **pydantic** can be really painful to work with.

— **[Kirill Podoprigora](https://github.com/Eclips4)**, CPython core developer

> Using `django-modern-rest` has been a game-changer for my productivity. The strict type safety and schema validation for both requests and responses mean I spend less time debugging and more time building.

— **[Josiah Kaviani](https://github.com/proofit404)**, Django core developer

> I rarely see frameworks that treat their OpenAPI schema as a first-class citizen. `django-modern-rest` not only generates a schema that accurately reflects your code, but also gives you the tools to verify it.

— **[Dmitry Dygalo](https://github.com/Stranger6667)**, author of Schemathesis

## Installation

Works for:
- CPython 3.11+ or PyPy 3.11+
- Django 4.2+

```bash
pip install django-modern-rest
```

There are several included extras:
- `'django-modern-rest[msgspec]'` provides `msgspec` support
  and the fastest json parsing, recommended to be **always** included
- `'django-modern-rest[pydantic]'` provides `pydantic` support
- `'django-modern-rest[attrs]'` provides `attrs` support
- `'django-modern-rest[jwt]'` provides [`pyjwt`](https://github.com/jpadilla/pyjwt) auth support
- `'django-modern-rest[openapi]'` provides `OpenAPI` [schema validation](https://github.com/python-openapi/openapi-spec-validator),
  `yaml` OpenAPI view,
  and generates better OpenAPI examples with [`polyfactory`](https://github.com/litestar-org/polyfactory)


## Example

The shortest example [(click here to copy the whole file)](https://github.com/wemake-services/django-modern-rest/blob/master/docs/examples/getting_started/pydantic_controller.py):

```python
>>> import uuid
>>> import pydantic
>>> from dmr import Body, Controller, Headers
>>> # Or use `dmr.plugins.msgspec` or write your own!
>>> from dmr.plugins.pydantic import PydanticFastSerializer

>>> class UserCreateModel(pydantic.BaseModel):
...     email: str

>>> class UserModel(UserCreateModel):
...     uid: uuid.UUID
...     consumer: str

>>> class HeaderModel(pydantic.BaseModel):
...     consumer: str = pydantic.Field(alias='X-API-Consumer')

>>> class UserController(Controller[PydanticFastSerializer]):
...     async def post(  # <- can be sync as well!
...         self,
...         parsed_body: Body[UserCreateModel],
...         parsed_headers: Headers[HeaderModel],
...     ) -> UserModel:
...         """All added props have the correct runtime and static types."""
...         return UserModel(
...             uid=uuid.uuid4(),
...             email=parsed_body.email,
...             consumer=parsed_headers.consumer,
...         )

```

And then route this controller in your `urls.py`:

```python
>>> from django.urls import include, path
>>> from dmr.routing import Router

>>> router = Router(
...     'api/',
...     [
...         path('user/', UserController.as_view(), name='users'),
...     ],
... )
>>> urlpatterns = [
...     path(router.prefix, include((router.urls, 'my_app'), namespace='api')),
... ]

```

Done! Now you have your shiny API with 100% type
safe validation and interactive docs.

Next steps:
- [The full documentation](https://django-modern-rest.rtfd.io) has everything you need to get started!
- [wemake-django-template](https://github.com/wemake-services/wemake-django-template) can be used to jump-start your new project with `django-modern-rest`!
- [awesome-django-modern-rest](https://github.com/kondratevdev/awesome-django-modern-rest) - a curated list of resources related to `django-modern-rest`!


## License

[MIT](https://github.com/wemake-services/django-modern-rest/blob/master/LICENSE)


## Credits

This project was generated with [`wemake-python-package`](https://github.com/wemake-services/wemake-python-package). Current template version is: [e1fcf312d7f715323dcff0d376a40b7e3b47f9b7](https://github.com/wemake-services/wemake-python-package/tree/e1fcf312d7f715323dcff0d376a40b7e3b47f9b7). See what is [updated](https://github.com/wemake-services/wemake-python-package/compare/e1fcf312d7f715323dcff0d376a40b7e3b47f9b7...master) since then.
