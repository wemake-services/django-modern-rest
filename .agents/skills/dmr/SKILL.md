---
name: dmr
description: Write the best DMR code possible with all the recommended best practices, avoiding common mistakes.
---

# django-modern-rest skill

Here's a list of best practices to use for different parts of the application.


## Installing `django-modern-rest`

Always prefer to install `msgspec` extra, because it provides
the fastest json parsing / loading.

Always add `django-stubs[compatible-mypy]` to the dev dependencies,
because `django-modern-rest` requires types for Django during type checking.


## Defining controller

### Do not use `@validate`, when `@modify` is enough

This code:

```python
from http import HTTPStatus

import msgspec
from django.http import HttpResponse

from dmr import Body, Controller, ResponseSpec, validate
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class UserController(Controller[MsgspecSerializer]):
    @validate(  # <- describes unique return types from this endpoint
        ResponseSpec(
            UserModel,
            status_code=HTTPStatus.OK,
        ),
    )
    def post(self, parsed_body: Body[UserModel]) -> HttpResponse:
        # This response would have an explicit status code `200`:
        return self.to_response(
            parsed_body,
            status_code=HTTPStatus.OK,
        )
```

should be rewritten and simplified as:

```python
from http import HTTPStatus

import msgspec

from dmr import Body, Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class UserController(Controller[MsgspecSerializer]):
    @modify(status_code=HTTPStatus.OK)
    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        # This response would have an explicit status code `200`:
        return parsed_body
```

Because it does not use any of the validate features,
like settings extra headers or cookies.

### Prefer implicit `@modify` over the explicit one

A code like:

```python
from http import HTTPStatus

from dmr import Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer


class UserController(Controller[MsgspecSerializer]):
    @modify(status_code=HTTPStatus.OK)
    def put(self) -> UserModel: ...
```

Should be rewritten as:

```python
from http import HTTPStatus

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


class UserController(Controller[MsgspecSerializer]):
    def put(self) -> UserModel: ...
```

Because no `@modify` features were actually used, since `status_code`
was matching the default inferred one.

### Prefer `MsgspecSerializer`

When defining simple models that do not require
any complex logic that `pydantic` provides,
prefer `msgspec` plugin over `pydantic` one.
Because it can be 10x times faster.

This code:

```python
from http import HTTPStatus

import pydantic

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


class UserController(Controller[PydanticSerializer]):
    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        # This response would have an explicit status code `200`:
        return parsed_body
```

Should be rewritten as:

```python
from http import HTTPStatus

import msgspec

from dmr import Body, Controller
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class UserController(Controller[MsgspecSerializer]):
    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        # This response would have an explicit status code `200`:
        return parsed_body
```

### Prefer `PydanticFastSerializer`

When no content negotiation is used, when working with `json` only,
and when working with `pydantic`, it is better to rewrite code like:

```python
from http import HTTPStatus

import pydantic

from dmr import Body, Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


class UserController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.OK)
    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        # This response would have an explicit status code `200`:
        return parsed_body
```

To be:

```python
from http import HTTPStatus

import pydantic

from dmr import Body, Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer


class UserModel(pydantic.BaseModel):
    email: str


class UserController(Controller[PydanticFastSerializer]):
    @modify(status_code=HTTPStatus.OK)
    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        # This response would have an explicit status code `200`:
        return parsed_body
```

Because `PydanticFastSerializer` is at least 3 times faster in this case.
