# Framework Patterns

Use these patterns as the canonical dmr translation targets for generated skeletons.

## Choose Components from HTTP Inputs

- Map JSON or form request bodies to `Body[RequestDto]`.
- Map query parameters to `Query[QueryDto]`.
- Map path parameters to `Path[PathDto]`.
- Map header parameters to `Headers[HeaderDto]`.
- Map cookie parameters to `Cookies[CookieDto]`.
- Map multipart file uploads to `FileMetadata[FileMetadataDto]` and use `self.parsed_file_metadata` for validated metadata.

Prefer `pydantic.BaseModel` DTOs for OpenAPI-driven work unless the repository already leans on msgspec.

## Use a Direct Controller for Single-Operation Routes

```python
import pydantic

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer


class UserCreateInput(pydantic.BaseModel):
    email: str


class UserOutput(UserCreateInput):
    id: int


class UserCreateController(
    Body[UserCreateInput],
    Controller[PydanticSerializer],
):
    def post(self) -> UserOutput:
        return UserOutput(id=1, email=self.parsed_body.email)
```

Use this shape when one route has one operation or when a single class naturally owns the endpoint.

## Correctly use controller for Multi-Method Paths

Prefer this shape for multi-method paths: keep several methods in one controller when they share the same logic and the same URL,
and split into multiple controllers only when there are different logical boundaries or URLs.

```python
from django.urls import path

from dmr import Controller, Body
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class UsersController(Controller[PydanticSerializer]):
    def get(self) -> list[UserOutput]:
        return []

    def post(self, parsed_body: Body[UserCreateInput]) -> UserOutput:
        return UserOutput(id=1, email=self.parsed_body.email)


router = Router(
    [
        path(
            'users/',
            UsersController.as_view(),
            name='users',
        ),
    ],
    prefix='accounts/',
)
```


## Use Explicit Response Metadata Only When Needed

Use direct return annotations for ordinary success responses.

Use `ResponseSpec` through `responses = (...)`, `@modify(...)`, or `@validate(...)` when:

- an operation documents extra error models
- an endpoint returns `HttpResponse`
- an endpoint has cookies or headers that must be declared
- a route has multiple success response shapes

Example:

```python
from http import HTTPStatus

from dmr import APIError, Controller, ResponseSpec, modify
from dmr.errors import ErrorModel, ErrorType
from dmr.plugins.pydantic import PydanticSerializer


class InvoiceController(Controller[PydanticSerializer]):
    @modify(
        extra_responses=[
            ResponseSpec(ErrorModel, status_code=HTTPStatus.CONFLICT),
        ],
    )
    def post(self) -> InvoiceOutput:
        raise APIError(
            self.format_error(
                'Conflict',
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.CONFLICT,
        )
```

## Represent Empty Responses Explicitly

Use this pattern for `204 No Content` and similar empty-body responses:

```python
from http import HTTPStatus

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class JobCreateController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self) -> None:
        return None
```

Do not attach `Body[...]` to HTTP methods that normally forbid request bodies unless the spec truly requires it and you intentionally override HTTP-spec validation.

## Wire Project-Level Docs Like a Normal Django Project

Use this shape only when the user asks for a runnable project skeleton with docs:

```python
from django.urls import include, path

from dmr.openapi import build_schema
from dmr.openapi.views import (
    OpenAPIJsonView,
    RedocView,
    ScalarView,
    StoplightView,
    SwaggerView,
)
from dmr.routing import Router

router = Router([...], prefix='api/')
schema = build_schema(router)

urlpatterns = [
    path(router.prefix, include((router.urls, 'server'), namespace='api')),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
    path('docs/redoc/', RedocView.as_view(schema), name='redoc'),
    path('docs/scalar/', ScalarView.as_view(schema), name='scalar'),
    path('docs/swagger/', SwaggerView.as_view(schema), name='swagger'),
    path('docs/stoplight/', StoplightView.as_view(schema), name='stoplight'),
]
```
