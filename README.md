<div align="center">
  <img src="https://raw.githubusercontent.com/wemake-services/django-modern-rest/master/docs/_static/images/logo-light.svg#gh-light-mode-only" alt="Modern REST Logo - Light" width="100%" height="auto" />
  <img src="https://raw.githubusercontent.com/wemake-services/django-modern-rest/master/docs/_static/images/logo-dark.svg#gh-dark-mode-only" alt="Modern REST Logo - Dark" width="100%" height="auto" />
</div>

<p align="center">
  <em>Modern REST framework for Django with types and async support!</em>
</p>

[![wemake.services](https://img.shields.io/badge/%20-wemake.services-green.svg?label=%20&logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAABGdBTUEAALGPC%2FxhBQAAAAFzUkdCAK7OHOkAAAAbUExURQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP%2F%2F%2F5TvxDIAAAAIdFJOUwAjRA8xXANAL%2Bv0SAAAADNJREFUGNNjYCAIOJjRBdBFWMkVQeGzcHAwksJnAPPZGOGAASzPzAEHEGVsLExQwE7YswCb7AFZSF3bbAAAAABJRU5ErkJggg%3D%3D)](https://wemake-services.github.io)
[![test](https://github.com/wemake-services/django-modern-rest/actions/workflows/test.yml/badge.svg?event=push)](https://github.com/wemake-services/django-modern-rest/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/wemake-services/django-modern-rest/branch/master/graph/badge.svg)](https://codecov.io/gh/wemake-services/django-modern-rest)
[![Python Version](https://img.shields.io/pypi/pyversions/django-modern-rest.svg)](https://pypi.org/project/django-modern-rest/)
[![wemake-python-styleguide](https://img.shields.io/badge/style-wemake-000000.svg)](https://github.com/wemake-services/wemake-python-styleguide)
</div>

## Features

- [x] [Blazingly fast](https://django-modern-rest.readthedocs.io/en/latest/pages/deep-dive/performance.html)
- [x] Fully typed and checked with `mypy` and `pyright` in strict modes
- [x] Strict schema validation of both requests and responses
- [x] Supports `pydantic2`, but not bound to it
- [x] Supports `msgspec`, but not bound to it
- [x] Strict schema validation for requests and responses
- [x] Supports async Django
- [ ] Supports `openapi` 3.1+ schema generation out of the box
- [x] Supports all your existing `django` primitives and packages, no custom runtimes
- [ ] Great testing tools with [schemathesis](https://github.com/schemathesis/schemathesis), [polyfactory](https://github.com/litestar-org/polyfactory), bundled `pytest` plugin, and default Django's testing primitives
- [x] 100% test coverage
- [x] Built [by the community](https://github.com/wemake-services/django-modern-rest/graphs/contributors) for the community, not a single-person project
- [x] Great docs
- [x] No emojis 🌚️️


<div align="center">
  <img src="https://raw.githubusercontent.com/wemake-services/django-modern-rest/master/docs/_static/images/benchmarks/sync-light.svg#gh-light-mode-only" alt="Benchmark - Light" width="100%" height="auto" />
  <img src="https://raw.githubusercontent.com/wemake-services/django-modern-rest/master/docs/_static/images/benchmarks/sync-dark.svg#gh-dark-mode-only" alt="Benchmakr - Dark" width="100%" height="auto" />
</div>

<p align="center">
  <em>Sync mode</em>
</p>


## Installation

Works for:
- Python 3.11+
- Django 4.2+

```bash
pip install django-modern-rest
```

There are several included extras:
- `'django-modern-rest[msgspec]'` provides `msgspec` support
  and the fastest json parsing, recommended to be **always** included
- `'django-modern-rest[pydantic]'` provides `pydantic` support


## Testimonials

> The one thing I really love about **django-modern-rest** is its pluggable
> serializers and validators. Frameworks that are tightly coupled
> with **pydantic** can be really painful to work with.

— **[Kirill Podoprigora](https://github.com/Eclips4)**, CPython core developer

> Using `django-modern-rest` has been a game-changer for my productivity. The strict type safety and schema validation for both requests and responses mean I spend less time debugging and more time building.

— **[Josiah Kaviani](https://github.com/proofit404)**, Django core developer

## Example

The shortest example:

```python
>>> import uuid
>>> import pydantic
>>> from django_modern_rest import Body, Controller, Headers
>>> # Or use `django_modern_rest.plugins.msgspec` or write your own!
>>> from django_modern_rest.plugins.pydantic import PydanticSerializer

>>> class UserCreateModel(pydantic.BaseModel):
...     email: str

>>> class UserModel(UserCreateModel):
...     uid: uuid.UUID

>>> class HeaderModel(pydantic.BaseModel):
...     consumer: str = pydantic.Field(alias='X-API-Consumer')

>>> class UserController(
...     Controller[PydanticSerializer],
...     Body[UserCreateModel],
...     Headers[HeaderModel],
... ):
...     def post(self) -> UserModel:  # <- can be async as well!
...         """All added props have the correct runtime and static types."""
...         assert self.parsed_headers.consumer == 'my-api'
...         return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)
```

And then route this controller in your `urls.py`:

```python
>>> from django.urls import include, path
>>> from django_modern_rest import Router

>>> router = Router([
...     path('user/', UserController.as_view(), name='users'),
... ])
>>> urlpatterns = [
...     path('api/', include((router.urls, 'your_app'), namespace='api')),
... ]
```

Done! Now you have your shiny API with 100% type
safe validation and interactive docs.

[The full documentation](https://django-modern-rest.rtfd.io)
has everything you need to get started!

[wemake-django-template](https://github.com/wemake-services/wemake-django-template)
can be used to jump-start your new project with `django-modern-rest`!


## License

[MIT](https://github.com/wemake-services/django-modern-rest/blob/master/LICENSE)


## Performance benchmarks

Prerequisites:
- Install `hyperfine`.

```bash
make bench-path
```

## Credits

This project was generated with [`wemake-python-package`](https://github.com/wemake-services/wemake-python-package). Current template version is: [e1fcf312d7f715323dcff0d376a40b7e3b47f9b7](https://github.com/wemake-services/wemake-python-package/tree/e1fcf312d7f715323dcff0d376a40b7e3b47f9b7). See what is [updated](https://github.com/wemake-services/wemake-python-package/compare/e1fcf312d7f715323dcff0d376a40b7e3b47f9b7...master) since then.
