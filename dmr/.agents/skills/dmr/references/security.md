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


## CSRF

### Turn CSRF checks on with `csrf_exempt = False`

`dmr` exempts every controller from CSRF checks by default.
Set `csrf_exempt = False` on a controller, and Django's `CsrfViewMiddleware`
checks its unsafe methods like for any Django view.
`dmr` then documents the `403` response and the `csrf` security scheme
for those methods on its own. Wrapping `csrf_protect` by hand repeats this
with more code and a worse schema: the `403` is documented for safe methods too,
and the converter runs on the status code alone, so every `403`
of the controller turns into a CSRF error.

Wrong:

```python
from http import HTTPStatus

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect

from dmr import Controller, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.errors import ErrorModel, format_error
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.response import build_response


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
class ProfileController(Controller[MsgspecSerializer]):
    responses = csrf_protect_json.responses

    def post(self) -> str:
        return 'updated'
```

Correct:

```python
from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


class ProfileController(Controller[MsgspecSerializer]):
    csrf_exempt = False

    def post(self) -> str:
        return 'updated'
```

Set `CSRF_FAILURE_VIEW` in `settings.py`, so failed checks under the API prefix
return the same JSON errors as the rest of the API:

```python
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security.csrf import build_csrf_handler

CSRF_FAILURE_VIEW = build_csrf_handler('api/', serializer=MsgspecSerializer)
```

`settings.py` cannot import the router, it would load the views
before Django is set up. To keep `router.prefix` as the only source,
build the handler in `urls.py` next to `handler404`
and set `CSRF_FAILURE_VIEW` to its dotted path, like `'server.urls.csrf_failure'`.

Clients send the `csrftoken` cookie and the same value
in the `X-CSRFToken` header. Django sets the cookie on login
and whenever `django.middleware.csrf.get_token` is called,
so a client without a login form can get it from an endpoint like this:

```python
from django.middleware.csrf import get_token

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


class CsrfTokenController(Controller[MsgspecSerializer]):
    def get(self) -> str:
        return get_token(self.request)
```

**Limitations:** `CsrfViewMiddleware` must be in `MIDDLEWARE`, without it
`csrf_exempt = False` checks nothing. `DjangoSessionSyncAuth`,
`CookieJWTSyncAuth`, and their async versions check CSRF themselves,
controllers that use them need no `csrf_exempt = False`.
`DMRClient` skips CSRF checks like Django's test client,
use `DMRClient(enforce_csrf_checks=True)` to test them.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/integrations.html#controller-csrf


## Middleware

### Wrap Django middleware with `wrap_middleware` to document its responses

Django decorators and middleware can answer before the endpoint runs,
like `condition` with `304 Not Modified`. Applied with `dispatch_decorator`
or `method_decorator`, these responses are missing from the OpenAPI schema
and keep whatever format Django gave them. `wrap_middleware` adds them
to the schema and passes them through your converter.
`dmr` does not validate them, so the converter must return
what its `ResponseSpec` describes.

Wrong:

```python
from django.http import HttpRequest
from django.views.decorators.http import condition

from dmr import Controller
from dmr.decorators import dispatch_decorator
from dmr.plugins.msgspec import MsgspecSerializer


def _catalog_etag(request: HttpRequest, **kwargs: object) -> str:
    return f'"catalog-{Catalog.objects.get().revision}"'


# `304` is not in OpenAPI and has no `Content-Type`:
@dispatch_decorator(condition(etag_func=_catalog_etag))
class CatalogController(Controller[MsgspecSerializer]):
    def get(self) -> list[str]:
        return ['book', 'pen']
```

Correct:

```python
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import condition

from dmr import Controller, HeaderSpec, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.plugins.msgspec import MsgspecSerializer


def _catalog_etag(request: HttpRequest, **kwargs: object) -> str:
    return f'"catalog-{Catalog.objects.get().revision}"'


@wrap_middleware(
    condition(etag_func=_catalog_etag),
    ResponseSpec(
        None,
        status_code=HTTPStatus.NOT_MODIFIED,
        headers={'ETag': HeaderSpec()},
    ),
)
def catalog_etag_json(response: HttpResponse) -> HttpResponse:
    # Django's `304` has no `Content-Type`:
    response['Content-Type'] = 'application/json'
    return response


@catalog_etag_json
class CatalogController(Controller[MsgspecSerializer]):
    responses = catalog_etag_json.responses

    def get(self) -> list[str]:
        return ['book', 'pen']
```

**Limitations:** `wrap_middleware` handles both sync and async automatically — always add `responses = wrapped_func.responses` to the controller for OpenAPI docs. Do not wrap `csrf_protect`, use `csrf_exempt = False` instead.

Docs:

- https://django-modern-rest.readthedocs.io/en/latest/pages/middleware.html
- https://django-modern-rest.readthedocs.io/en/latest/pages/integrations.html#conditional-requests-etag
