# django-modern-rest

[![test](https://github.com/wemake-services/django-modern-rest/actions/workflows/test.yml/badge.svg?event=push)](https://github.com/wemake-services/django-modern-rest/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/wemake-services/django-modern-rest/branch/master/graph/badge.svg)](https://codecov.io/gh/wemake-services/django-modern-rest)
[![Python Version](https://img.shields.io/pypi/pyversions/django-modern-rest.svg)](https://pypi.org/project/django-modern-rest/)
[![wemake-python-styleguide](https://img.shields.io/badge/style-wemake-000000.svg)](https://github.com/wemake-services/wemake-python-styleguide)

Modern REST framework for Django with types and async support!


## Features

- [x] Blazingly fast
- [x] Fully typed and checked with `mypy` and `pyright` in strict modes
- [x] Strict schema validation of both requests and responses
- [x] Supports `pydantic2`, but not bound to it
- [x] Supports `msgspec`, but not bound to it
- [x] Supports async Django
- [ ] Supports `openapi` schema generation out of the box
- [x] Supports all your existing `django` primitives and packages
- [ ] Great testing tools with [schemathesis](https://github.com/schemathesis/schemathesis), [polyfactory](https://github.com/litestar-org/polyfactory), bundled `pytest` plugin, and default Django's testing primitives
- [x] Does not use `from __future__ import annotations`
- [x] 100% test coverage
- [x] No emojis 🌚️️


## Installation

```bash
pip install django-modern-rest
```

There are several included extras:
- `'django-modern-rest[msgspec]'` provides `msgspec` support
  and the fastest json parsing, recommended to be **always** included
- `'django-modern-rest[pydantic]'` provides `pydantic` support


## Example

1. The shortest example:

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
...     token: str = pydantic.Field(alias='X-API-Token')

>>> class UserController(
...     Controller[PydanticSerializer],
...     Body[UserCreateModel],
...     Headers[HeaderModel],
... ):
...     def post(self) -> UserModel:
...         """All added props have the correct runtime and static types."""
...         assert self.parsed_headers.token == 'secret!'
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

Done! Now you have your shiny API with 100% type safe validation and interactive docs.

2. Also single file API is supported

Paste in `main.py` file code snippet below
```python
import uuid

import pydantic
from django.conf import settings
from django.core.handlers import wsgi
from django.urls import include, path

from django_modern_rest import Body, Controller, Headers, Router

# Or use `django_modern_rest.plugins.msgspec` or write your own!
from django_modern_rest.plugins.pydantic import PydanticSerializer

settings.configure(
    # Keep it as is
    ROOT_URLCONF=__name__,
    # Required options but feel free to configure as you like
    DMR_SETTINGS={},
    ALLOWED_HOSTS="*",
)

app = wsgi.WSGIHandler()

class UserCreateModel(pydantic.BaseModel):
    email: str

class UserModel(UserCreateModel):
    uid: uuid.UUID

class HeaderModel(pydantic.BaseModel):
    token: str = pydantic.Field(alias='X-API-Token')

class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
    Headers[HeaderModel],
):
    def post(self) -> UserModel:
        """All added props have the correct runtime and static types"""
        assert self.parsed_headers.token == 'secret!'
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)

router = Router([
     path('user/', UserController.as_view(), name='users'),
 ])
urlpatterns = [
     path('api/', include((router.urls, 'your_app'), namespace='api')),
]

```
Then run it via wsgi server. Let's use `gunicorn`
```bash
gunicorn main:app
```
Ensure API works
```bash
curl -X POST \
--url "http://127.0.0.1:8000/api/user/" \
-H "Content-Type: application/json" \
-H "X-API-Token: secret\!" \
-d '{"email": "example@example.com"}'
```


## License

[MIT](https://github.com/wemake-services/django-modern-rest/blob/master/LICENSE)


## Credits

This project was generated with [`wemake-python-package`](https://github.com/wemake-services/wemake-python-package). Current template version is: [e1fcf312d7f715323dcff0d376a40b7e3b47f9b7](https://github.com/wemake-services/wemake-python-package/tree/e1fcf312d7f715323dcff0d376a40b7e3b47f9b7). See what is [updated](https://github.com/wemake-services/wemake-python-package/compare/e1fcf312d7f715323dcff0d376a40b7e3b47f9b7...master) since then.
