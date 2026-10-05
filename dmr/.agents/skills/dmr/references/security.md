# Authentication, throttling, and middleware

Reference for the `dmr` skill. Loaded on demand, see [SKILL.md](../SKILL.md).


## Authentication

### Route `concrete_views` instead of writing auth controllers that change nothing

Every auth flow ships ready-to-use login, refresh, verify, and logout controllers
in a `concrete_views` module next to its `views` module.
They already take the default payloads, return the default responses,
and set `auth = None`, so only a serializer is missing.
A subclass of a reusable `views` controller that passes the payload through
and builds the default response by hand is the same controller,
only with more code to maintain.

Wrong:

```python
import datetime as dt

from typing_extensions import override

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router, path
from dmr.security.jwt.views import (
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
)


class ObtainTokensController(
    ObtainTokensSyncController[
        MsgspecSerializer,
        ObtainTokensPayload,
        ObtainTokensResponse,
    ],
):
    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload  # nothing is converted

    @override
    def make_api_response(self) -> ObtainTokensResponse:
        now = dt.datetime.now(dt.UTC)
        return {  # the default response, written by hand
            'access_token': self.create_jwt_token(
                expiration=now + self.jwt_expiration,
                token_type='access',
            ),
            'refresh_token': self.create_jwt_token(
                expiration=now + self.jwt_refresh_expiration,
                token_type='refresh',
            ),
        }


router = Router(
    'api/',
    [path('auth/', ObtainTokensController.as_view(), name='jwt_obtain')],
)
```

Correct:

```python
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router, path
from dmr.security.jwt import concrete_views

router = Router(
    'api/',
    [
        path(
            'auth/',
            concrete_views.ObtainTokensSyncController.as_view(
                serializer=MsgspecSerializer,
            ),
            name='jwt_obtain',
        ),
        path(
            'auth/refresh/',
            concrete_views.RefreshTokenSyncController.as_view(
                serializer=MsgspecSerializer,
            ),
            name='jwt_refresh',
        ),
    ],
)
```

Pick the controllers of the auth flow the project uses,
each one has a `Sync` and an `Async` version:

| Auth flow | Module | Controllers |
| --- | --- | --- |
| JWT in the response body | `dmr.security.jwt.concrete_views` | `ObtainTokens*`, `RefreshToken*`, `VerifyToken*` |
| JWT in cookies | `dmr.security.jwt.concrete_views` | `CookieObtainTokens*`, `CookieRefreshTokens*`, `CookieLogout*` |
| Opaque tokens | `dmr.security.token.concrete_views` | `ObtainToken*` |
| Django session | `dmr.security.django_session.concrete_views` | `DjangoSession*` |

`as_view` requires `serializer=` and passes other keyword arguments
to Django as `initkwargs`, so settings like `jwt_expiration=` need no subclass either.
Two settings are typed keyword arguments of `as_view`:

- `token_cls=` on the opaque token controllers,
  pass it when the project swaps the bundled `Token` model.
- `jwt_refresh_cookie_path=` on the cookie controllers.
  It defaults to `'/'`, which sends the refresh token with every request.
  Point it to the refresh endpoint on all three cookie controllers:

```python
from typing import Final

from django.urls import reverse_lazy

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router, path
from dmr.security.jwt import concrete_views

REFRESH_COOKIE_PATH: Final = reverse_lazy('api:jwt_refresh')

router = Router(
    'api/',
    [
        path(
            'auth/',
            concrete_views.CookieObtainTokensSyncController.as_view(
                serializer=MsgspecSerializer,
                jwt_refresh_cookie_path=REFRESH_COOKIE_PATH,
            ),
            name='jwt_obtain',
        ),
        path(
            'auth/refresh/',
            concrete_views.CookieRefreshTokensSyncController.as_view(
                serializer=MsgspecSerializer,
                jwt_refresh_cookie_path=REFRESH_COOKIE_PATH,
            ),
            name='jwt_refresh',
        ),
        path(
            'auth/logout/',
            concrete_views.CookieLogoutSyncController.as_view(
                serializer=MsgspecSerializer,
                jwt_refresh_cookie_path=REFRESH_COOKIE_PATH,
            ),
            name='jwt_logout',
        ),
    ],
)

urlpatterns = [router.to_urlpatterns(namespace='api')]
```

`as_view` only sets instance attributes, while `throttling`, `auth`,
`responses`, and other endpoint metadata are read from the class.
Passing them to `as_view` is silently ignored, the endpoint stays unthrottled.
Concrete views use `Settings.throttling` from `DMR_SETTINGS`,
like every controller without its own `throttling`.
When the login endpoint needs its own throttle, it really differs
from the defaults: subclass the reusable `views` controller for it
and keep `concrete_views` for the rest:

```python
import datetime as dt

from typing_extensions import override

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router, path
from dmr.security.jwt import concrete_views
from dmr.security.jwt.views import (
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
)
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr


class LoginController(
    ObtainTokensSyncController[
        MsgspecSerializer,
        ObtainTokensPayload,
        ObtainTokensResponse,
    ],
):
    # Reusable views do not set it, auth from the settings must not apply:
    auth = None
    # This is what `concrete_views.ObtainTokensSyncController` cannot do:
    throttling = (SyncThrottle(5, Rate.minute, cache_key=RemoteAddr()),)

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload

    @override
    def make_api_response(self) -> ObtainTokensResponse:
        now = dt.datetime.now(dt.UTC)
        return {
            'access_token': self.create_jwt_token(
                expiration=now + self.jwt_expiration,
                token_type='access',
            ),
            'refresh_token': self.create_jwt_token(
                expiration=now + self.jwt_refresh_expiration,
                token_type='refresh',
            ),
        }


router = Router(
    'api/',
    [
        path('auth/', LoginController.as_view(), name='jwt_obtain'),
        path(
            'auth/refresh/',
            concrete_views.RefreshTokenSyncController.as_view(
                serializer=MsgspecSerializer,
            ),
            name='jwt_refresh',
        ),
    ],
)
```

**Limitations:** `concrete_views` were added in `0.16.0`.
They are final: do not subclass them.
Subclass the reusable `views` controller only when something
really differs from the defaults: the payload (login by email),
the response body (extra fields), a hook (`make_token_name`, `login`),
or endpoint metadata like a login-specific `throttling`.

Docs:

- https://django-modern-rest.readthedocs.io/en/latest/pages/auth/jwt.html#jwt-concrete-views
- https://django-modern-rest.readthedocs.io/en/latest/pages/auth/token.html#token-concrete-views
- https://django-modern-rest.readthedocs.io/en/latest/pages/auth/django-session.html#django-session-concrete-views

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

**Limitations:** `runs_before_auth=True` is the default for `RemoteAddr`, so you only need to be explicit when switching it off for non-auth endpoints. Ready-to-use `concrete_views` ignore `throttling=` passed to `as_view`, see [Route `concrete_views` instead of writing auth controllers that change nothing](#route-concrete_views-instead-of-writing-auth-controllers-that-change-nothing).

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
