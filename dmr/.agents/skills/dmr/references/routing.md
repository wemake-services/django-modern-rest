# Routing and project structure

Reference for the `dmr` skill. Loaded on demand, see [SKILL.md](../SKILL.md).


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

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/routing.html

### Use `build_404_handler` for API-style 404 responses

`build_404_handler` returns JSON 404 responses for API prefixes while keeping Django HTML 404s for non-API paths.

Wrong:

```python
from django.urls import include

from dmr.routing import Router, path
from myapp.views import UserController

router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
]
# No custom 404 handler — API gets HTML error pages
```

Correct:

```python
from django.urls import include

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router, build_404_handler, path
from myapp.views import UserController

router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
]

handler404 = build_404_handler(router.prefix, serializer=MsgspecSerializer)
```

**Limitations:** overriding `handler404` has no effect while `DEBUG = True` — this is Django's default behavior.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/routing.html

### Use `build_500_handler` for API-style 500 responses

`build_500_handler` returns JSON 500 responses for API prefixes while keeping Django HTML 500s for non-API paths.

Wrong:

```python
from django.urls import include

from dmr.routing import Router, path
from myapp.views import UserController

router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
]
# No custom 500 handler — API gets HTML error pages
```

Correct:

```python
from django.urls import include

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router, build_500_handler, path
from myapp.views import UserController

router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
]

handler500 = build_500_handler(router.prefix, serializer=MsgspecSerializer)
```

**Limitations:** overriding `handler500` has no effect while `DEBUG = True` — this is Django's default behavior.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/routing.html


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

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/structure/sync-and-async.html
