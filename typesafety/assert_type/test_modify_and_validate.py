from http import HTTPStatus

import pydantic
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _

from dmr import (
    Controller,
    CookieSpec,
    HeaderSpec,
    NewHeader,
    ResponseSpec,
    modify,
    validate,
)
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)
from dmr.serializer import BaseSerializer
from dmr.throttling import AsyncThrottle, SyncThrottle


class _Model(pydantic.BaseModel):
    field: str


def _sync_error_handler(
    endpoint: Endpoint,
    controller: Controller[BaseSerializer],
    exc: Exception,
) -> HttpResponse:
    raise exc


async def _async_error_handler(
    endpoint: Endpoint,
    controller: Controller[BaseSerializer],
    exc: Exception,
) -> HttpResponse:
    raise exc


class CorrectModifyController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.OK, description='Test GET endpoint')
    def get(self) -> str:
        return 'Done'

    @modify(
        status_code=HTTPStatus.OK,
        summary=_('Test'),
        description=_('Test POST endpoint'),
    )
    async def post(self) -> int:
        return 1

    @modify(
        headers={
            'X-Custom': NewHeader(
                value='Example',
                description='Header test description',
            ),
        },
        description='Test PATCH endpoint',
    )
    def patch(self) -> int:
        return 1

    @modify(description='Test PUT endpoint')  # no args
    async def put(self) -> int:
        return 1

    @modify(headers={'X-Custom': HeaderSpec(skip_validation=True)})
    def delete(self) -> int:
        return 1

    @modify(cookies={'X-Custom': CookieSpec(skip_validation=True)})
    def trace(self) -> int:
        return 1


class CorrectValidateController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        summary=_('Test'),
        description=_('Test get endpoint'),
    )
    def get(self) -> HttpResponse:
        return HttpResponse()

    @validate(
        ResponseSpec(return_type=list[int], status_code=HTTPStatus.OK),
    )
    async def post(self) -> JsonResponse:
        return JsonResponse([])

    @validate(
        ResponseSpec(
            return_type=list[int],
            status_code=HTTPStatus.OK,
            headers={
                'X-Custom': HeaderSpec(
                    description='Header test description',
                ),
            },
        ),
    )
    async def put(self) -> JsonResponse:
        return JsonResponse([])


class WrongModifyController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.OK)  # type: ignore[deprecated]
    def get(self) -> JsonResponse:
        return JsonResponse([])

    @modify(status_code=HTTPStatus.OK)  # type: ignore[deprecated]
    async def post(self) -> HttpResponse:
        return HttpResponse()

    @modify()  # type: ignore[deprecated]
    def put(self) -> HttpResponse:
        return HttpResponse()


class WrongValidateController(Controller[PydanticSerializer]):
    @validate(  # type: ignore[type-var]  # ty: ignore[invalid-argument-type]
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
    )
    def get(self) -> int:
        return 1

    @validate(  # type: ignore[type-var]  # ty: ignore[invalid-argument-type]
        ResponseSpec(return_type=list[int], status_code=HTTPStatus.OK),
    )
    async def post(self) -> str:
        return 'a'

    # Not enough params:
    @validate(ResponseSpec(return_type=list[int]))  # type: ignore[call-arg]  # ty: ignore[missing-argument]
    async def put(self) -> JsonResponse:
        return JsonResponse([])

    @validate(
        ResponseSpec(
            return_type=list[int],
            status_code=HTTPStatus.OK,
            headers={'X-Custom': NewHeader(value=1)},  # type: ignore[dict-item, arg-type]  # ty: ignore[invalid-argument-type]
        ),
    )
    def patch(self) -> JsonResponse:
        return JsonResponse([])

    @validate()  # type: ignore[call-overload, untyped-decorator]  # ty: ignore[no-matching-overload, dynamic-function-decorator-return]
    async def delete(self) -> HttpResponse:
        return JsonResponse([])


class WrongAuthMixedController(Controller[PydanticSerializer]):
    auth = (DjangoSessionSyncAuth(), DjangoSessionAsyncAuth())  # type: ignore[assignment]

    @modify(auth=[DjangoSessionSyncAuth(), DjangoSessionAsyncAuth()])  # type: ignore[list-item]  # ty: ignore[no-matching-overload, dynamic-function-decorator-return]
    def get(self) -> str:
        return 'mixed'

    @validate(  # pyrefly: ignore[no-matching-overload] # ty: ignore[no-matching-overload, dynamic-function-decorator-return]
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        auth=[DjangoSessionSyncAuth(), DjangoSessionAsyncAuth()],  # type: ignore[list-item]
    )
    async def meta(self) -> HttpResponse:
        return HttpResponse()

    @modify(auth=[DjangoSessionAsyncAuth()])  # type: ignore[deprecated]
    def wrong_async_auth(self) -> str:
        return 'mixed'

    @modify(auth=[DjangoSessionSyncAuth()])  # type: ignore[deprecated]
    async def wrong_sync_auth(self) -> str:
        return 'mixed'

    @validate(  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        auth=[DjangoSessionAsyncAuth()],
    )
    def wrong_async_auth_validate(self) -> HttpResponse:
        return HttpResponse()

    @validate(  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        auth=[DjangoSessionSyncAuth()],
    )
    async def wrong_sync_auth_validate(self) -> HttpResponse:
        return HttpResponse()


class WrongThrottlingMixedController(Controller[PydanticSerializer]):
    throttling = (SyncThrottle(1, 2), AsyncThrottle(1, 2))  # type: ignore[assignment]

    @modify(throttling=[SyncThrottle(1, 2), AsyncThrottle(1, 2)])  # type: ignore[list-item]  # ty: ignore[no-matching-overload, dynamic-function-decorator-return]
    def get(self) -> str:
        return 'mixed'

    @validate(  # pyrefly: ignore[no-matching-overload] # ty: ignore[no-matching-overload, dynamic-function-decorator-return]
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        throttling=[SyncThrottle(1, 2), AsyncThrottle(1, 2)],  # type: ignore[list-item]
    )
    async def meta(self) -> HttpResponse:
        return HttpResponse()

    @modify(throttling=[AsyncThrottle(1, 2)])  # type: ignore[deprecated]
    def wrong_async_throttle(self) -> str:
        return 'mixed'

    @modify(throttling=[SyncThrottle(1, 2)])  # type: ignore[deprecated]
    async def wrong_sync_throttle(self) -> str:
        return 'mixed'

    @validate(  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        throttling=[AsyncThrottle(1, 2)],
    )
    def wrong_async_throttle_validate(self) -> HttpResponse:
        return HttpResponse()

    @validate(  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        throttling=[SyncThrottle(1, 2)],
    )
    async def wrong_sync_throttle_validate(self) -> HttpResponse:
        return HttpResponse()

    # Different kinds mixed together:
    @modify(  # pyrefly: ignore[no-matching-overload] # ty: ignore[no-matching-overload, dynamic-function-decorator-return]
        auth=[DjangoSessionSyncAuth()],  # type: ignore[list-item]
        throttling=[AsyncThrottle(1, 2)],  # type: ignore[list-item]
    )
    def mixed_kinds(self) -> str:
        return 'mixed'


class CorrectColoredController(Controller[PydanticSerializer]):
    @modify(
        auth=[DjangoSessionSyncAuth()],
        throttling=[SyncThrottle(1, 2)],
        error_handler=_sync_error_handler,
    )
    def get(self) -> str:
        return 'sync'

    @modify(
        auth=[DjangoSessionAsyncAuth()],
        throttling=[AsyncThrottle(1, 2)],
        error_handler=_async_error_handler,
    )
    async def post(self) -> str:
        return 'async'

    # `ty` infers `list[Unknown]` for an empty list literal,
    # so it matches several overloads and gives up on the return type:
    @modify(auth=None, throttling=[])  # ty: ignore[dynamic-function-decorator-return]
    def put(self) -> str:
        return 'sync'

    @modify(auth=(), throttling=None)
    async def patch(self) -> str:
        return 'async'

    @validate(
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        auth=[DjangoSessionSyncAuth()],
        throttling=[SyncThrottle(1, 2)],
        error_handler=_sync_error_handler,
    )
    def delete(self) -> HttpResponse:
        return HttpResponse()

    @validate(
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        auth=[DjangoSessionAsyncAuth()],
        throttling=[AsyncThrottle(1, 2)],
        error_handler=_async_error_handler,
    )
    async def trace(self) -> HttpResponse:
        return HttpResponse()

    @validate(
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        auth=None,
        throttling=(),
    )
    async def head(self) -> HttpResponse:
        return HttpResponse()


class WrongErrorHandlerController(Controller[PydanticSerializer]):
    @modify(error_handler=_async_error_handler)  # type: ignore[deprecated]
    def get(self) -> str:
        return 'sync'

    @modify(error_handler=_sync_error_handler)  # type: ignore[deprecated]
    async def post(self) -> str:
        return 'async'

    @validate(  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        error_handler=_async_error_handler,
    )
    def put(self) -> HttpResponse:
        return HttpResponse()

    @validate(  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        ResponseSpec(status_code=HTTPStatus.OK, return_type=_Model),
        error_handler=_sync_error_handler,
    )
    async def delete(self) -> HttpResponse:
        return HttpResponse()

    @modify(  # pyrefly: ignore[no-matching-overload] # ty: ignore[no-matching-overload, dynamic-function-decorator-return]
        auth=[DjangoSessionAsyncAuth()],
        error_handler=_sync_error_handler,  # type: ignore[arg-type]
    )
    async def patch(self) -> str:
        return 'mixed'
