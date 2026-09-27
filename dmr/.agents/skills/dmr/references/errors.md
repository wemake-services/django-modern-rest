# Error handling

Reference for the `dmr` skill. Loaded on demand, see [SKILL.md](../SKILL.md).


## Error handling

### Match error handler sync/async type to the endpoint type

Async endpoints require async error handlers, and sync endpoints require sync error handlers — this is validated on endpoint creation.

Wrong:

```python
from http import HTTPStatus

from django.http import HttpResponse

from dmr import Controller, modify
from dmr.endpoint import Endpoint
from dmr.plugins.msgspec import MsgspecSerializer
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


class MyController(Controller[MsgspecSerializer]):
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
from dmr.plugins.msgspec import MsgspecSerializer
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


class MyController(Controller[MsgspecSerializer]):
    @modify(error_handler=async_error_handler)
    async def get(self) -> str:
        return 'hello'
```

**Limitations:** the same rule applies to controller-level `handle_error` (sync) and `handle_async_error` (async) — don't define sync handlers for async controllers and vice versa.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/error-handling.html

### Don't catch `APIError` explicitly in error handlers

`APIError` has a built-in default handler that automatically converts it to an `HttpResponse` — you don't need to handle it manually.

Wrong:

```python
from http import HTTPStatus

from django.http import HttpResponse
from typing_extensions import override

from dmr import APIError, Controller
from dmr.endpoint import Endpoint
from dmr.plugins.msgspec import MsgspecSerializer


class MyController(Controller[MsgspecSerializer]):
    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[MsgspecSerializer],
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
from dmr.plugins.msgspec import MsgspecSerializer


class MyController(Controller[MsgspecSerializer]):
    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[MsgspecSerializer],
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

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/error-handling.html

### Customize error messages with `error_model` and `format_error` on the controller

Defining a custom `error_model` and overriding `format_error` on the controller gives consistent error formatting across all endpoints and updates the OpenAPI schema automatically.

Wrong:

```python
from http import HTTPStatus

from dmr import APIError, Controller
from dmr.plugins.msgspec import MsgspecSerializer


class MyController(Controller[MsgspecSerializer]):
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
from dmr.plugins.msgspec import MsgspecSerializer


class CustomErrorDetail(TypedDict):
    message: str


class CustomErrorModel(TypedDict):
    errors: list[CustomErrorDetail]


class MyController(Controller[MsgspecSerializer]):
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

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/error-handling.html

### Do not handle errors in the endpoints body

We have a separate layer in the app specifically for error handling.
Instead of handling errors in place, prefer to use the error handling methods,
like `handle_error` and `handle_async_error`.

Wrong:

```python
from http import HTTPStatus

from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.plugins.msgspec import MsgspecSerializer

from myapp import SomeSpecificError, some_logic


class MyController(Controller[MsgspecSerializer]):
    def get(self) -> str:
        try:
            return some_logic()
        except SomeSpecificError:
            return self.to_error(
                self.format_error(str(exc)),
                status_code=HTTPStatus.BAD_REQUEST,
            )
```

Correct:

```python
from http import HTTPStatus

from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.plugins.msgspec import MsgspecSerializer

from myapp import SomeSpecificError, some_logic


class MyController(Controller[MsgspecSerializer]):
    def get(self) -> str:
        return some_logic()

    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[MsgspecSerializer],
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, SomeSpecificError):
            return self.to_error(
                self.format_error(str(exc)),
                status_code=HTTPStatus.BAD_REQUEST,
            )
        raise exc from None
```

If error is handled in most controllers, you can move it to a global handler.
