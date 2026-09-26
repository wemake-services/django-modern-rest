# Controllers, components, and redirects

Reference for the `dmr` skill. Loaded on demand, see [SKILL.md](../SKILL.md).


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

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/using-controller/index.html

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

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/deep-dive/public-api.html#dmr.plugins.pydantic.PydanticFastSerializer

### Never return Django `HttpResponse` directly — use `to_response`, `to_error`, or `APIError`

Returning Django responses directly bypasses content negotiation, cookie and header management.

Wrong:

```python
import json

from django.http import HttpResponse

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


class UserController(Controller[MsgspecSerializer]):
    def get(self) -> HttpResponse:
        return HttpResponse(
            json.dumps({'email': 'user@example.com'}),
            content_type='application/json',
            headers={'X-API-Token': 'some-token'},
            status=200,
        )
```

Correct:

```python
import msgspec

from django.http import HttpResponse

from dmr import Body, Controller, validate
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class UserController(Controller[MsgspecSerializer]):
    def get(self) -> HttpResponse:
        return self.to_response(
            {'email': 'user@example.com'},
            headers={'X-API-Token': 'some-token'},
        )
```

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/using-controller/index.html

### Use `APIError` for error responses instead of manually building `HttpResponse`

`APIError` is automatically handled by the framework, formatted through `format_error`, and documented in OpenAPI schema.

Wrong:

```python
import json
from http import HTTPStatus

from django.http import HttpResponse

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


class UserController(Controller[MsgspecSerializer]):
    def get(self) -> HttpResponse:
        return HttpResponse(
            json.dumps({'detail': [{'msg': 'Not found'}]}),
            content_type='application/json',
            status=404,
        )
```

Correct:

```python
from http import HTTPStatus

from dmr import APIError, Controller
from dmr.errors import ErrorType
from dmr.plugins.msgspec import MsgspecSerializer


class UserController(Controller[MsgspecSerializer]):
    def get(self) -> str:
        raise APIError(
            self.format_error(
                'Not found',
                error_type=ErrorType.user_msg,
            ),
            status_code=HTTPStatus.NOT_FOUND,
        )
```

You can also use `self.to_error` when using `@validate` endpoints.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/error-handling.html


## Components

### Always name parsed body as `parsed_body` and parsed query as `parsed_query`

The framework uses parameter names `parsed_body` and `parsed_query` to identify which components to inject — using other names silently skips parsing.

Wrong:

```python
import msgspec

from dmr import Body, Controller, Query
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class FilterModel(msgspec.Struct):
    active: bool = True


class UserController(Controller[MsgspecSerializer]):
    def post(
        self,
        body: Body[UserModel],  # wrong name!
        query: Query[FilterModel],  # wrong name!
    ) -> UserModel:
        return body
```

Correct:

```python
import msgspec

from dmr import Body, Controller, Query
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class FilterModel(msgspec.Struct):
    active: bool = True


class UserController(Controller[MsgspecSerializer]):
    def post(
        self,
        parsed_body: Body[UserModel],
        parsed_query: Query[FilterModel],
    ) -> UserModel:
        return parsed_body
```

**Limitations:** this naming convention also applies to `parsed_headers: Headers[...]`, `parsed_path: Path[...]`, and `parsed_cookies: Cookies[...]`.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/components/index.html


## Redirects

### Choose a redirect compatible with the endpoint style

Raise `RedirectTo` from `@modify` endpoints, because they cannot return
`HttpResponse` subclasses. `@validate` endpoints support both raising
`RedirectTo` and returning Django's `HttpResponseRedirect` equally. Returning
`HttpResponseRedirect` from `@validate` is an exception to the general rule
against returning Django responses directly.

Whichever redirect style you use, document the `Location` header in its
`ResponseSpec`. For `@modify`, add the spec to `extra_responses`; for
`@validate`, pass the spec directly:

```python
from http import HTTPStatus
from typing import Final

from django.http import HttpResponse, HttpResponseRedirect

from dmr import (
    Controller,
    HeaderSpec,
    RedirectTo,
    ResponseSpec,
    modify,
    validate,
)
from dmr.plugins.msgspec import MsgspecSerializer

_REDIRECT_SPEC: Final = ResponseSpec(
    None,
    status_code=HTTPStatus.FOUND,
    headers={'Location': HeaderSpec()},
)


class UserController(Controller[MsgspecSerializer]):
    @modify(extra_responses=[_REDIRECT_SPEC])
    def get(self) -> str:
        raise RedirectTo(
            '/api/new/users/',
            status_code=HTTPStatus.FOUND,
        )

    @validate(_REDIRECT_SPEC)
    def post(self) -> HttpResponse:
        raise RedirectTo(
            '/api/new/users/',
            status_code=HTTPStatus.FOUND,
        )

    @validate(_REDIRECT_SPEC)
    def put(self) -> HttpResponseRedirect:
        return HttpResponseRedirect(
            '/api/new/users/',
            content_type='application/json',
        )
```

Select the redirect status code according to the
[Redirection 3xx section of the HTTP Semantics specification][http-redirects].

[http-redirects]: https://www.rfc-editor.org/rfc/rfc9110.html#name-redirection-3xx

### Validate user-provided URLs before passing them to `RedirectTo`

`RedirectTo` validates a URL's length and scheme, but does not check whether
the destination host is trusted. Passing an untrusted URL directly can create
an open redirect vulnerability.

Wrong:

```python
from typing import Never

from dmr import RedirectTo


def redirect_to_next(next_url: str) -> Never:
    raise RedirectTo(next_url)
```

Correct:

```python
from typing import Never

from django.http import HttpRequest
from django.utils.http import url_has_allowed_host_and_scheme

from dmr import RedirectTo


def redirect_to_next(request: HttpRequest, next_url: str) -> Never:
    url_is_safe = url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    raise RedirectTo(next_url if url_is_safe else '/')
```

**Limitations:** validation is required for user-provided or otherwise
untrusted redirect targets; hard-coded local URLs do not need this check.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/using-controller/redirects.html
