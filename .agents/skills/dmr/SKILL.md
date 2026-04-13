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

### Never return Django `HttpResponse` directly — use `to_response`, `to_error`, or `APIError`

Returning Django responses directly bypasses response validation, content negotiation, and header management.

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
            status=200,
        )
```

Correct:

```python
import msgspec

from dmr import Body, Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class UserController(Controller[MsgspecSerializer]):
    def get(self) -> UserModel:
        return UserModel(email='user@example.com')
```

**Limitations:** `@validate` endpoints must return `HttpResponse` via `self.to_response()` — this rule applies to `@modify` / raw endpoints only.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/using-controller/index.html

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

**Limitations:** you don't need to catch `APIError` in error handlers — it has a default handler that converts it to `HttpResponse` automatically.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/error-handling.html

### Use `TypeVar` for generic reusable controllers

Using `TypeVar` for the serializer parameter lets you create controllers that work with any serializer plugin.

Wrong:

```python
from typing_extensions import TypedDict

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class _ResponseBody(TypedDict):
    message: str


class ReusableController(Controller[PydanticSerializer]):
    def get(self) -> _ResponseBody:
        return {'message': 'hello'}
```

Correct:

```python
from typing import TypeVar

from typing_extensions import TypedDict

from dmr import Controller
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)


class _ResponseBody(TypedDict):
    message: str


class ReusableController(Controller[_SerializerT]):
    def get(self) -> _ResponseBody:
        serializer_name = self.serializer.__name__
        return {'message': f'hello from {serializer_name}'}
```

**Limitations:** concrete subclasses must specify the actual serializer type — schema generation and validation work on concrete types only.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/reusable-code.html


## Routing

### Use `dmr.routing.path` instead of `django.urls.path`

`dmr.routing.path` is a drop-in replacement that uses prefix-based pattern matching for 9-31% faster URL routing.

Wrong:

```python
from django.urls import include, path

urlpatterns = [
    path('api/', include('myapp.urls')),
]
```

Correct:

```python
from django.urls import include

from dmr.routing import path

urlpatterns = [
    path('api/', include('myapp.urls')),
]
```

**Limitations:** no API changes required — it is a full drop-in replacement for `django.urls.path`.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/routing.html

### Use `build_404_handler` for API-style 404 responses

`build_404_handler` returns JSON 404 responses for API prefixes while keeping Django HTML 404s for non-API paths.

Wrong:

```python
from django.urls import include

from dmr.routing import Router, path
from myapp.views import UserController

router = Router('api/', [
    path('user/', UserController.as_view(), name='users'),
])

urlpatterns = [
    path(router.prefix, include((router.urls, 'app'), namespace='api')),
]
# No custom 404 handler — API gets HTML error pages
```

Correct:

```python
from django.urls import include

from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, build_404_handler, path
from myapp.views import UserController

router = Router('api/', [
    path('user/', UserController.as_view(), name='users'),
])

urlpatterns = [
    path(router.prefix, include((router.urls, 'app'), namespace='api')),
]

handler404 = build_404_handler(router.prefix, serializer=PydanticSerializer)
```

**Limitations:** overriding `handler404` has no effect while `DEBUG = True` — this is Django's default behavior.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/routing.html

### Use `build_500_handler` for API-style 500 responses

`build_500_handler` returns JSON 500 responses for API prefixes while keeping Django HTML 500s for non-API paths.

Wrong:

```python
from django.urls import include

from dmr.routing import Router, path
from myapp.views import UserController

router = Router('api/', [
    path('user/', UserController.as_view(), name='users'),
])

urlpatterns = [
    path(router.prefix, include((router.urls, 'app'), namespace='api')),
]
# No custom 500 handler — API gets HTML error pages
```

Correct:

```python
from django.urls import include

from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, build_500_handler, path
from myapp.views import UserController

router = Router('api/', [
    path('user/', UserController.as_view(), name='users'),
])

urlpatterns = [
    path(router.prefix, include((router.urls, 'app'), namespace='api')),
]

handler500 = build_500_handler(router.prefix, serializer=PydanticSerializer)
```

**Limitations:** overriding `handler500` has no effect while `DEBUG = True` — this is Django's default behavior.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/routing.html


## Error handling

### Match error handler sync/async type to the endpoint type

Async endpoints require async error handlers, and sync endpoints require sync error handlers — this is validated on endpoint creation.

Wrong:

```python
from http import HTTPStatus

from django.http import HttpResponse

from dmr import Controller, modify
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer


def sync_error_handler(
    endpoint: Endpoint,
    controller: Controller[BaseSerializer],
    exc: Exception,
) -> HttpResponse:
    return controller.to_error(
        controller.format_error(str(exc)),
        status_code=HTTPStatus.BAD_REQUEST,
    )


class MyController(Controller[PydanticSerializer]):
    @modify(error_handler=sync_error_handler)
    async def get(self) -> str:  # async endpoint with sync handler!
        return 'hello'
```

Correct:

```python
from http import HTTPStatus

from django.http import HttpResponse

from dmr import Controller, modify
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer


async def async_error_handler(
    endpoint: Endpoint,
    controller: Controller[BaseSerializer],
    exc: Exception,
) -> HttpResponse:
    return controller.to_error(
        controller.format_error(str(exc)),
        status_code=HTTPStatus.BAD_REQUEST,
    )


class MyController(Controller[PydanticSerializer]):
    @modify(error_handler=async_error_handler)
    async def get(self) -> str:
        return 'hello'
```

**Limitations:** the same rule applies to controller-level `handle_error` (sync) and `handle_async_error` (async) — don't define sync handlers for async controllers and vice versa.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/error-handling.html

### Don't catch `APIError` explicitly in error handlers

`APIError` has a built-in default handler that automatically converts it to an `HttpResponse` — you don't need to handle it manually.

Wrong:

```python
from http import HTTPStatus

from django.http import HttpResponse
from typing_extensions import override

from dmr import APIError, Controller
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer


class MyController(Controller[PydanticSerializer]):
    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[PydanticSerializer],
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, APIError):  # unnecessary!
            return self.to_error(
                exc.args[0],
                status_code=exc.status_code,
            )
        raise exc from None
```

Correct:

```python
from http import HTTPStatus

from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer


class MyController(Controller[PydanticSerializer]):
    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[PydanticSerializer],
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, SomeSpecificError):
            return self.to_error(
                self.format_error(str(exc)),
                status_code=HTTPStatus.BAD_REQUEST,
            )
        raise exc from None
```

**Limitations:** only catch specific errors you know how to handle — always re-raise unfamiliar errors to let the next handler level deal with them.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/error-handling.html

### Customize error messages with `error_model` and `format_error` on the controller

Defining a custom `error_model` and overriding `format_error` on the controller gives consistent error formatting across all endpoints and updates the OpenAPI schema automatically.

Wrong:

```python
from http import HTTPStatus

from dmr import APIError, Controller
from dmr.plugins.pydantic import PydanticSerializer


class MyController(Controller[PydanticSerializer]):
    def post(self) -> str:
        raise APIError(
            {'errors': [{'message': 'test'}]},  # ad-hoc format
            status_code=HTTPStatus.BAD_REQUEST,
        )
```

Correct:

```python
from http import HTTPStatus
from typing import Any

from typing_extensions import TypedDict, override

from dmr import APIError, Body, Controller, ResponseSpec, modify
from dmr.errors import ErrorType, format_error
from dmr.plugins.pydantic import PydanticSerializer


class CustomErrorDetail(TypedDict):
    message: str


class CustomErrorModel(TypedDict):
    errors: list[CustomErrorDetail]


class MyController(Controller[PydanticSerializer]):
    error_model = CustomErrorModel

    @override
    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> Any:
        default = format_error(error, loc=loc, error_type=error_type)
        return {
            'errors': [
                {'message': detail['msg']} for detail in default['detail']
            ],
        }

    @modify(
        extra_responses=[
            ResponseSpec(
                return_type=CustomErrorModel,
                status_code=HTTPStatus.BAD_REQUEST,
            ),
        ],
    )
    def post(self, parsed_body: Body[dict[str, str]]) -> str:
        raise APIError(
            self.format_error('test msg'),
            status_code=HTTPStatus.BAD_REQUEST,
        )
```

**Limitations:** `error_model` and `format_error` are per-controller — you can't customize error format per-endpoint, only per-controller or globally.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/error-handling.html


## Validation

### Disable response validation in production, keep it on in development

Response validation catches schema mismatches during development, but adds overhead in production — disable it globally for deployed apps.

Wrong:

```python
# settings.py — production with validation still on (slow):
DMR_SETTINGS = {}  # validate_responses defaults to True
```

Correct:

```python
# settings.py — production:
from dmr.settings import Settings

DMR_SETTINGS = {
    Settings.validate_responses: False,
}
```

**Limitations:** only disable for production — fix schema errors during development instead of turning off validation.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/validation.html

### Don't override `HttpSpec` validation unless implementing legacy APIs

`HttpSpec` validation is already disabled by default for problematic cases — overriding it should only be done for very specific legacy API compatibility reasons.

Wrong:

```python
from http import HTTPStatus

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import HttpSpec


class JobController(Controller[PydanticSerializer]):
    # Disabling just to avoid fixing the real issue:
    no_validate_http_spec = frozenset((HttpSpec.empty_response_body,))

    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self) -> int:
        return 4
```

Correct:

```python
from http import HTTPStatus

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class JobController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self) -> None:
        print('Job created')  # noqa: WPS421
```

**Limitations:** override `no_validate_http_spec` only when implementing old legacy APIs that cannot follow HTTP spec properly.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/validation.html


## Authentication

### Disable auth per-endpoint, never globally via `Settings.auth = None`

Setting `auth=None` on a specific endpoint makes that endpoint public while keeping all others protected.

Wrong:

```python
# settings.py — this disables auth for ALL endpoints with no way to re-enable:
from dmr.settings import Settings

DMR_SETTINGS = {
    Settings.auth: None,
}
```

Correct:

```python
from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import JWTAsyncAuth


class APIController(Controller[PydanticSerializer]):
    auth = (JWTAsyncAuth(),)

    async def get(self) -> str:
        return 'protected'

    @modify(auth=[])
    async def post(self) -> str:  # public endpoint (e.g., registration)
        return 'public'
```

**Limitations:** multiple auth instances use OR logic — at least one must succeed for the request to be authenticated.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/auth/common.html

### Use typed request for authenticated controllers

Annotating `self.request` with a typed subclass of `HttpRequest` gives type-safe access to the authenticated user.

Wrong:

```python
from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionSyncAuth


class APIController(Controller[PydanticSerializer]):
    auth = (DjangoSessionSyncAuth(),)

    def get(self) -> str:
        # self.request.user is `AbstractBaseUser | AnonymousUser` by default:
        return f'hello {self.request.user}'
```

Correct:

```python
from django.contrib.auth.models import User
from django.http import HttpRequest

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionSyncAuth


class AuthenticatedHttpRequest(HttpRequest):
    user: User


class APIController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest
    auth = (DjangoSessionSyncAuth(),)

    def get(self) -> str:
        # self.request.user is now typed as `User`:
        return f'hello {self.request.user.username}'
```

**Limitations:** the typed request annotation is for type checking only — it does not enforce the user type at runtime.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/auth/django-session.html


## Throttling

### Prefer HTTP proxy rate limiting over Django-level throttling

HTTP proxy rate limiting (e.g., nginx, Cloudflare) is significantly faster and more secure than application-level throttling.

Wrong:

```python
# Using Django-level throttling as the sole rate limiter for high-traffic public APIs:
from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.throttling import SyncThrottle, Rate


class PublicAPIController(Controller[PydanticSerializer]):
    throttling = (SyncThrottle(100, Rate.minute),)

    def get(self) -> str:
        return 'data'
```

Correct:

```python
# Configure rate limiting at the proxy level (nginx, Cloudflare, etc.)
# and use Django throttling only for fine-grained per-endpoint control:
from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.throttling import SyncThrottle, Rate


class PublicAPIController(Controller[PydanticSerializer]):
    # Fine-grained throttle for expensive operations only:
    @modify(throttling=[SyncThrottle(10, Rate.minute)])
    def post(self) -> str:
        return 'created'

    def get(self) -> str:  # rate-limited by proxy
        return 'data'
```

**Limitations:** this only applies when you have an HTTP proxy in front of Django — if Django is directly exposed, application-level throttling is necessary.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/throttling.html

### Protect auth endpoints with throttling BEFORE authentication

Always throttle authentication endpoints before auth runs to prevent brute force attacks — use `runs_before_auth=True` (default) on cache keys.

Wrong:

```python
from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr


class LoginController(Controller[PydanticSerializer]):
    @modify(
        auth=[DjangoSessionSyncAuth()],
        throttling=[
            SyncThrottle(
                5,
                Rate.minute,
                cache_key=RemoteAddr(runs_before_auth=False),
            ),
        ],
    )
    def post(self) -> str:  # throttle runs AFTER auth — brute force possible!
        return 'logged in'
```

Correct:

```python
from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr


class LoginController(Controller[PydanticSerializer]):
    @modify(
        auth=[DjangoSessionSyncAuth()],
        throttling=[
            SyncThrottle(
                5,
                Rate.minute,
                cache_key=RemoteAddr(runs_before_auth=True),
            ),
        ],
    )
    def post(self) -> str:  # throttle runs BEFORE auth — brute force prevented
        return 'logged in'
```

**Limitations:** `runs_before_auth=True` is the default for `RemoteAddr`, so you only need to be explicit when switching it off for non-auth endpoints.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/throttling.html


## Testing

### Use `DMRClient` and `DMRRequestFactory` instead of plain Django test tools

`DMRClient` and `DMRRequestFactory` default `Content-Type` to `application/json`, simplifying JSON API testing.

Wrong:

```python
import json

from django.test import TestCase


class TestUsers(TestCase):
    def test_create_user(self) -> None:
        response = self.client.post(
            '/users/',
            data=json.dumps({'email': 'user@example.com', 'age': 20}),
            content_type='application/json',
        )
        assert response.status_code == 201
```

Correct:

```python
from django.test import TestCase
from typing_extensions import override

from dmr.test import DMRClient


class TestUsers(TestCase):
    @override
    def setUp(self) -> None:
        self.client = DMRClient()

    def test_create_user(self) -> None:
        response = self.client.post(
            '/users/',
            data={'email': 'user@example.com', 'age': 20},
        )
        assert response.status_code == 201
```

**Limitations:** for async controllers, use `DMRAsyncRequestFactory` and `DMRAsyncClient` instead.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/testing.html

### Use `DMRRequestFactory` for faster unit tests

`DMRRequestFactory` allows testing controllers directly without going through Django's URL routing and middleware, making tests significantly faster.

Wrong:

```python
import json

from django.test import TestCase
from typing_extensions import override

from dmr.test import DMRClient


class TestUsers(TestCase):
    @override
    def setUp(self) -> None:
        self.client = DMRClient()

    def test_create_user(self) -> None:
        # Full HTTP request through URL routing and middleware:
        response = self.client.post(
            '/users/',
            data={'email': 'user@example.com', 'age': 20},
        )
        assert response.status_code == 201
```

Correct:

```python
import json
from http import HTTPStatus

from django.http import HttpResponse

from dmr.test import DMRRequestFactory
from myapp.views import UserController


def test_create_user() -> None:
    dmr_rf = DMRRequestFactory()
    payload = {'email': 'user@example.com', 'age': 20}

    request = dmr_rf.post('/users/', data=payload)
    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
```

**Limitations:** `DMRRequestFactory` tests skip URL routing and middleware — use `DMRClient` when you need to test the full request/response cycle.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/testing.html

### Use `Polyfactory` for structured test data generation

`Polyfactory` generates random test data from your model types, helping you find unexpected corner cases without manually crafting payloads.

Wrong:

```python
from dmr.test import DMRRequestFactory
from myapp.views import UserController


def test_create_user(dmr_rf: DMRRequestFactory) -> None:
    # Manually crafted payload — misses edge cases:
    request = dmr_rf.post('/url/', data={'email': 'a@b.com', 'age': 20})
    response = UserController.as_view()(request)
    assert response.status_code == 201
```

Correct:

```python
from polyfactory.factories.pydantic_factory import ModelFactory

from dmr.test import DMRRequestFactory
from myapp.views import UserController, UserCreateModel


class UserCreateModelFactory(ModelFactory[UserCreateModel]):
    __check_model__ = True


def test_create_user(dmr_rf: DMRRequestFactory) -> None:
    request_data = UserCreateModelFactory.build().model_dump(mode='json')
    request = dmr_rf.post('/url/', data=request_data)
    response = UserController.as_view()(request)
    assert response.status_code == 201
```

**Limitations:** `Polyfactory` supports `pydantic`, `msgspec`, `@dataclass`, and `TypedDict` models — check its docs for your specific model type.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/testing.html

### Use `schemathesis` for property-based API testing

`schemathesis` generates thousands of tests from your OpenAPI schema, and in simple cases can eliminate the need for hand-written integration tests.

Wrong:

```python
# Manually writing integration tests for every endpoint:
from dmr.test import DMRClient


def test_get_users(dmr_client: DMRClient) -> None:
    response = dmr_client.get('/api/users/')
    assert response.status_code == 200


def test_get_users_invalid(dmr_client: DMRClient) -> None:
    response = dmr_client.get('/api/users/?page=-1')
    assert response.status_code == 422
# ... many more tests for each edge case
```

Correct:

```python
import schemathesis
from django.test.utils import override_settings


@override_settings(ROOT_URLCONF='myapp.urls')
def test_api(api_schema: schemathesis.from_url) -> None:
    schema = schemathesis.from_url(api_schema)

    @schema.parametrize()
    def test_endpoint(case: schemathesis.Case) -> None:
        case.call_and_validate()
```

**Limitations:** `schemathesis` is not bundled with `django-modern-rest` — install it separately with `uv add --group dev schemathesis`.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/testing.html


## Middleware

### Wrap Django middleware with `wrap_middleware` to keep OpenAPI docs and validation

`wrap_middleware` ensures middleware responses are documented in OpenAPI schema and subject to response validation.

Wrong:

```python
from django.views.decorators.csrf import csrf_protect

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


@csrf_protect  # not tracked in OpenAPI, no response validation
class ProtectedController(Controller[PydanticSerializer]):
    def post(self) -> dict[str, str]:
        return {'message': 'created'}
```

Correct:

```python
from http import HTTPStatus

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect

from dmr import Controller, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.errors import ErrorModel
from dmr.plugins.pydantic import PydanticSerializer


@wrap_middleware(
    csrf_protect,
    ResponseSpec(
        return_type=ErrorModel,
        status_code=HTTPStatus.FORBIDDEN,
    ),
)
def csrf_protect_json(response: HttpResponse) -> HttpResponse:
    return response


@csrf_protect_json
class ProtectedController(Controller[PydanticSerializer]):
    responses = csrf_protect_json.responses

    def post(self) -> dict[str, str]:
        return {'message': 'created'}
```

**Limitations:** `wrap_middleware` handles both sync and async automatically — always add `responses = wrapped_func.responses` to the controller for OpenAPI docs.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/middleware.html


## Configuration

### Enable `semantic_responses` for automatic error response documentation

`semantic_responses=True` automatically injects common error responses (auth errors, validation errors, throttling) into your OpenAPI schema.

Wrong:

```python
# settings.py — no semantic responses, error schemas missing from OpenAPI:
from dmr.settings import Settings

DMR_SETTINGS = {
    Settings.semantic_responses: False,
}
```

Correct:

```python
# settings.py:
from dmr.settings import Settings

DMR_SETTINGS = {
    Settings.semantic_responses: True,
}
```

**Limitations:** you can exclude specific status codes from semantic responses using `Settings.exclude_semantic_responses` if they don't apply to your API.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/configuration.html

### Always have at least one default parser and renderer in settings

Settings must always include at least one parser and one renderer for fallback error handling — even if you override parsers/renderers on controllers.

Wrong:

```python
# settings.py — no parsers/renderers at all:
from dmr.settings import Settings

DMR_SETTINGS = {
    Settings.parsers: [],
    Settings.renderers: [],
}
```

Correct:

```python
# settings.py:
from dmr.settings import Settings

DMR_SETTINGS = {
    # Default JSON parsers/renderers are included automatically
    # when not specified — don't set empty lists.
}
```

**Limitations:** custom parsers and renderers can be added per-controller or per-endpoint on top of the global defaults.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/configuration.html


## Project structure

### Separate sync and async into different application instances

Running sync and async endpoints in separate Django instances avoids the threadpool overhead and performance penalty of mixed sync/async handling.

Wrong:

```python
# urls.py — mixing sync and async in one URL config:
from dmr.routing import path

from myapp.views import AsyncUserController, SyncUserController

urlpatterns = [
    path('sync-users/', SyncUserController.as_view()),
    path('async-users/', AsyncUserController.as_view()),
]
# Running with a single gunicorn or uvicorn process
```

Correct:

```python
# urls.py — sync endpoints only:
from dmr.routing import path

from myapp.views import SyncUserController

urlpatterns = [
    path('users/', SyncUserController.as_view()),
]

# async_urls.py — async endpoints only:
from dmr.routing import path

from myapp.views import AsyncUserController

urlpatterns = [
    path('users/', AsyncUserController.as_view()),
]

# Run sync with gunicorn, async with uvicorn
# Route in proxy: /async/* → uvicorn, others → gunicorn
```

**Limitations:** this pattern is only beneficial for larger applications — small apps with few endpoints can safely mix sync and async in one instance.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/structure/sync-and-async.html


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

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/components/index.html


## Content negotiation

### Set parsers and renderers per-controller or per-endpoint when needed

Configuring content negotiation at the most specific level avoids affecting unrelated endpoints.

Wrong:

```python
# settings.py — forcing XML support globally for one controller's needs:
from dmr.settings import Settings
from myapp.negotiation import XmlParser, XmlRenderer

DMR_SETTINGS = {
    Settings.parsers: [XmlParser()],
    Settings.renderers: [XmlRenderer()],
}
```

Correct:

```python
from dmr import Body, Controller
from dmr.plugins.msgspec import MsgspecJsonParser, MsgspecJsonRenderer
from dmr.plugins.pydantic import PydanticSerializer
from myapp.negotiation import XmlParser, XmlRenderer


class UserController(Controller[PydanticSerializer]):
    parsers = (MsgspecJsonParser(), XmlParser())
    renderers = (MsgspecJsonRenderer(), XmlRenderer())

    def post(self, parsed_body: Body[dict[str, str]]) -> dict[str, str]:
        return parsed_body
```

**Limitations:** settings-level parsers/renderers still serve as the default fallback — always keep at least one parser and one renderer in global settings.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/negotiation.html


## Streaming

### Only use streaming for single-directional event streams

Streaming is designed for SSE and JSONL event streams (LLM responses, logs, telemetry) — don't use it for regular request/response patterns.

Wrong:

```python
from collections.abc import AsyncIterator

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming.sse import SSEController


class UserController(SSEController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[dict[str, str]]:
        # Using streaming for a single response:
        yield {'email': 'user@example.com'}
```

Correct:

```python
import msgspec

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class UserController(Controller[MsgspecSerializer]):
    def get(self) -> UserModel:
        return UserModel(email='user@example.com')
```

**Limitations:** all streaming requires Django running in ASGI mode in production — streaming controllers won't work with WSGI.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/streaming/common.html


## OpenAPI

### Add docstrings to controllers and endpoints for OpenAPI descriptions

Controller and endpoint docstrings are automatically used as descriptions in the generated OpenAPI schema.

Wrong:

```python
from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class UserController(Controller[PydanticSerializer]):
    def get(self) -> str:
        return 'hello'

    def post(self) -> str:
        return 'created'
```

Correct:

```python
from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class UserController(Controller[PydanticSerializer]):
    """Manage user accounts."""

    def get(self) -> str:
        """Retrieve the current user profile."""
        return 'hello'

    def post(self) -> str:
        """Create a new user account."""
        return 'created'
```

**Limitations:** docstrings only populate the `description` field in OpenAPI — use `@modify` or `@validate` for operation-level customization of other OpenAPI fields.

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/openapi/openapi.html


## Integrations

### CSRF is exempt by default — enable it explicitly for session-authenticated controllers

Controllers have `csrf_exempt = True` by default, which is correct for token-based auth — set `csrf_exempt = False` only when using Django session auth.

Wrong:

```python
from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionSyncAuth


class ProtectedController(Controller[PydanticSerializer]):
    # csrf_exempt defaults to True, but session auth needs CSRF:
    auth = (DjangoSessionSyncAuth(),)

    def post(self) -> str:
        return 'created'
```

Correct:

```python
from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionSyncAuth


class ProtectedController(Controller[PydanticSerializer]):
    csrf_exempt = False
    auth = (DjangoSessionSyncAuth(),)

    def post(self) -> str:
        return 'created'
```

**Limitations:** Django session auth automatically enables CSRF for security — for JWT or token auth, keep `csrf_exempt = True` (the default).

Docs: https://django-modern-rest.rtfd.io/en/latest/pages/integrations.html
