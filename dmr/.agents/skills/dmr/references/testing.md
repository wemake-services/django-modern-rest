# Testing

Reference for the `dmr` skill. Loaded on demand, see [SKILL.md](../SKILL.md).


## Testing

### Prefer `pytest` style test cases over `django.test.TestCase` ones

Wrong:

```python
from django.test import TestCase
from typing_extensions import override

from dmr.test import DMRRequestFactory
from myapp.views import UserController


class TestUsers(TestCase):
    @override
    def setUp(self) -> None:
        self.rf = DMRRequestFactory()

    def test_create_user(self) -> None:
        request = self.rf.get('/users/', content_type='application/json')

        response = UserController.as_view()(request)

        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.CREATED
```

Correct:

```python
from http import HTTPStatus

from django.http import HttpResponse

from dmr.test import DMRRequestFactory
from myapp.views import UserController


def test_create_user(dmr_rf: DMRRequestFactory) -> None:
    request = dmr_rf.get('/users/')

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
```

### Use `DMRClient` and `DMRRequestFactory` instead of plain Django test tools

`DMRClient` and `DMRRequestFactory` default `Content-Type` to `application/json`, simplifying JSON API testing.

Wrong:

```python
from http import HTTPStatus

from django.http import HttpResponse

from django.test import RequestFactory
from myapp.views import UserController


def test_create_user(rf: RequestFactory) -> None:
    request = dmr_rf.get('/users/', content_type='application/json')

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
```

Correct:

```python
from http import HTTPStatus

from django.http import HttpResponse

from dmr.test import DMRRequestFactory
from myapp.views import UserController


def test_create_user(dmr_rf: DMRRequestFactory) -> None:
    request = dmr_rf.get('/users/')

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
```

**Limitations:** for async controllers, use `DMRAsyncRequestFactory` and `DMRAsyncClient` instead.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/testing/tools-and-styles.html

### Use `DMRRequestFactory` for faster unit tests

`DMRRequestFactory` allows testing controllers directly without going through Django's URL routing and middleware, making tests significantly faster.

Wrong:

```python
from http import HTTPStatus

from django.http import HttpResponse

from dmr.test import DMRClient


def test_create_user(dmr_client: DMRClient) -> None:
    response = dmr_client.get('/users/')

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
```

Correct:

```python
from http import HTTPStatus

from django.http import HttpResponse

from dmr.test import DMRRequestFactory
from myapp.views import UserController


def test_create_user(dmr_rf: DMRRequestFactory) -> None:
    request = dmr_rf.get('/users/')

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
```

**Limitations:** `DMRRequestFactory` tests skip URL routing and middleware — use `DMRClient` when you need to test the full request/response cycle.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/testing/tools-and-styles.html

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
    # Enables strict model validation during factory builds:
    __check_model__ = True


def test_create_user(dmr_rf: DMRRequestFactory) -> None:
    request_data = UserCreateModelFactory.build().model_dump(mode='json')
    request = dmr_rf.post('/url/', data=request_data)
    response = UserController.as_view()(request)
    assert response.status_code == 201
```

**Limitations:** `Polyfactory` supports `pydantic`, `msgspec`, `@dataclass`, and `TypedDict` models — check its docs for your specific model type.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/testing/data-generation.html

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

Correct: use `schemathesis`. Check its official docs for more details.
https://schemathesis.readthedocs.io/en/stable/

**Limitations:** `schemathesis` is not bundled with `django-modern-rest` — install it separately with `uv add --group dev schemathesis`.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/testing/property-based.html
