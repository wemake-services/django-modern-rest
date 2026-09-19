# Authentication, throttling, and middleware

Reference for the `dmr` skill. Loaded on demand, see [SKILL.md](../SKILL.md).


## Authentication

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
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.django_session import DjangoSessionSyncAuth


class APIController(Controller[MsgspecSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (DjangoSessionSyncAuth(),)

    def get(self) -> str:
        # self.request.user is now typed as `User`:
        return f'hello {self.request.user.username}'
```

**Limitations:** the typed request annotation is for type checking only — it does not enforce the user type at runtime.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/auth/django-session.html


## Throttling

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
                cache_key=RemoteAddr(),
            ),
        ],
    )
    def post(self) -> str:  # throttle runs BEFORE auth — brute force prevented
        return 'logged in'
```

**Limitations:** `runs_before_auth=True` is the default for `RemoteAddr`, so you only need to be explicit when switching it off for non-auth endpoints.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/throttling.html


## Middleware

### Wrap Django middleware with `wrap_middleware` to keep OpenAPI docs and validation

`wrap_middleware` ensures middleware responses are documented in OpenAPI schema and subject to response validation.

Wrong:

```python
from django.views.decorators.csrf import csrf_protect

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


@csrf_protect  # not tracked in OpenAPI, no response validation
class ProtectedController(Controller[MsgspecSerializer]):
    def post(self) -> dict[str, str]:
        return {'message': 'created'}
```

Correct:

```python
from http import HTTPStatus

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect

from dmr import Controller, ResponseSpec
from dmr.response import build_response
from dmr.decorators import wrap_middleware
from dmr.errors import ErrorModel, format_error
from dmr.plugins.msgspec import MsgspecSerializer


@wrap_middleware(
    csrf_protect,
    ResponseSpec(
        return_type=ErrorModel,
        status_code=HTTPStatus.FORBIDDEN,
    ),
)
def csrf_protect_json(response: HttpResponse) -> HttpResponse:
    return build_response(
        MsgspecSerializer,
        raw_data=format_error('csrf error'),
        status_code=HTTPStatus.FORBIDDEN,
    )


@csrf_protect_json
class ProtectedController(Controller[MsgspecSerializer]):
    responses = csrf_protect_json.responses

    def post(self) -> dict[str, str]:
        return {'message': 'created'}
```

**Limitations:** `wrap_middleware` handles both sync and async automatically — always add `responses = wrapped_func.responses` to the controller for OpenAPI docs.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/middleware.html
