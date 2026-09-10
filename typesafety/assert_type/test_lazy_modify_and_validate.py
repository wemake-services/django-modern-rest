from http import HTTPStatus
from typing import final

from django.http import HttpResponse

from dmr import (
    Controller,
    ResponseSpec,
    modify,
    validate,
)
from dmr.endpoint import (
    ModifyAnyCallable,
    ModifyAsyncCallable,
    ModifySyncCallable,
    ValidateAnyCallable,
    ValidateAsyncCallable,
    ValidateSyncCallable,
)
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)


@final
class CorrectModify(Controller[PydanticSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _sync_spec(cls) -> ModifySyncCallable:
        return modify(
            status_code=cls.status_code,
            auth=[DjangoSessionSyncAuth()],
        )

    @modify.lazy(_sync_spec)  # ty: ignore[invalid-argument-type]
    def get(self) -> int:
        return 1

    @classmethod
    def _async_spec(cls) -> ModifyAsyncCallable:
        return modify(
            status_code=cls.status_code,
            auth=[DjangoSessionAsyncAuth()],
        )

    @modify.lazy(_async_spec)  # ty: ignore[invalid-argument-type]
    async def post(self) -> int:
        return 1

    @classmethod
    def _any_spec(cls) -> ModifyAnyCallable:
        return modify(status_code=cls.status_code)

    @modify.lazy(_any_spec)  # ty: ignore[invalid-argument-type]
    async def put(self) -> int:
        return 1

    @modify.lazy(_any_spec)  # ty: ignore[invalid-argument-type]
    def patch(self) -> int:
        return 1


@final
class AsyncAndSyncMixedModify(Controller[PydanticSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _sync_spec(cls) -> ModifySyncCallable:
        return modify(  # type: ignore[return-value]
            status_code=cls.status_code,
            auth=[DjangoSessionAsyncAuth()],
        )

    @modify.lazy(_sync_spec)  # type: ignore[deprecated]  # ty: ignore[invalid-argument-type]
    async def get(self) -> int:
        return 1

    @modify.lazy(_sync_spec)  # type: ignore[deprecated]  # ty: ignore[invalid-argument-type]
    def post(self) -> HttpResponse:
        return self.to_response(1)


@final
class SyncAndAsyncMixedModify(Controller[PydanticSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _async_spec(cls) -> ModifyAsyncCallable:
        return modify(  # type: ignore[return-value]
            status_code=cls.status_code,
            auth=[DjangoSessionSyncAuth()],
        )

    @modify.lazy(_async_spec)  # type: ignore[deprecated]  # ty: ignore[invalid-argument-type]
    def get(self) -> int:
        return 1

    @modify.lazy(_async_spec)  # type: ignore[deprecated]  # ty: ignore[invalid-argument-type]
    async def post(self) -> HttpResponse:
        return self.to_response(1)


@final
class AnyMixedModify(Controller[PydanticSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _any_spec(cls) -> ModifyAnyCallable:
        return modify(  # type: ignore[return-value]
            status_code=cls.status_code,
            auth=[DjangoSessionSyncAuth()],
        )

    @modify.lazy(_any_spec)  # ty: ignore[invalid-argument-type]
    def get(self) -> int:
        return 1

    @modify.lazy(_any_spec)  # ty: ignore[invalid-argument-type]
    async def put(self) -> int:
        return 1

    @modify.lazy(_any_spec)  # type: ignore[deprecated]  # ty: ignore[invalid-argument-type]
    async def post(self) -> HttpResponse:
        return self.to_response(1)


# Validate tests


@final
class CorrectValidate(Controller[PydanticSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _sync_spec(cls) -> ValidateSyncCallable:
        return validate(
            ResponseSpec(int, status_code=cls.status_code),
            auth=[DjangoSessionSyncAuth()],
        )

    @validate.lazy(_sync_spec)  # ty: ignore[invalid-argument-type]
    def get(self) -> HttpResponse:
        return self.to_response(1)

    @classmethod
    def _async_spec(cls) -> ValidateAsyncCallable:
        return validate(
            ResponseSpec(int, status_code=cls.status_code),
            auth=[DjangoSessionAsyncAuth()],
        )

    @validate.lazy(_async_spec)  # ty: ignore[invalid-argument-type]
    async def post(self) -> HttpResponse:
        return self.to_response(1)

    @classmethod
    def _any_spec(cls) -> ValidateAnyCallable:
        return validate(ResponseSpec(int, status_code=cls.status_code))

    @validate.lazy(_any_spec)  # ty: ignore[invalid-argument-type]
    async def put(self) -> HttpResponse:
        return self.to_response(1)

    @validate.lazy(_any_spec)  # ty: ignore[invalid-argument-type]
    def patch(self) -> HttpResponse:
        return self.to_response(1)


@final
class AsyncAndSyncMixedValidate(Controller[PydanticSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _sync_spec(cls) -> ValidateSyncCallable:
        return validate(  # type: ignore[return-value]
            ResponseSpec(int, status_code=cls.status_code),
            auth=[DjangoSessionAsyncAuth()],
        )

    @validate.lazy(_sync_spec)  # type: ignore[type-var]  # ty: ignore[invalid-argument-type]
    async def get(self) -> HttpResponse:
        return self.to_response(1)

    @validate.lazy(_sync_spec)  # type: ignore[type-var]  # ty: ignore[invalid-argument-type]
    def post(self) -> int:
        return 1


@final
class SyncAndAsyncMixedValidate(Controller[PydanticSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _async_spec(cls) -> ValidateAsyncCallable:
        return validate(  # type: ignore[return-value]
            ResponseSpec(int, status_code=cls.status_code),
            auth=[DjangoSessionSyncAuth()],
        )

    @validate.lazy(_async_spec)  # type: ignore[type-var]  # ty: ignore[invalid-argument-type]
    def get(self) -> HttpResponse:
        return self.to_response(1)

    @validate.lazy(_async_spec)  # type: ignore[type-var]  # ty: ignore[invalid-argument-type]
    async def post(self) -> int:
        return 1


@final
class AnyMixedValidate(Controller[PydanticSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _any_spec(cls) -> ValidateAnyCallable:
        return validate(  # type: ignore[return-value]
            ResponseSpec(int, status_code=cls.status_code),
            auth=[DjangoSessionSyncAuth()],
        )

    @validate.lazy(_any_spec)  # ty: ignore[invalid-argument-type]
    def get(self) -> HttpResponse:
        return self.to_response(1)

    @validate.lazy(_any_spec)  # ty: ignore[invalid-argument-type]
    async def put(self) -> HttpResponse:
        return self.to_response(1)

    @validate.lazy(_any_spec)  # type: ignore[type-var]  # ty: ignore[invalid-argument-type]
    async def post(self) -> int:
        return 1


# Common tests


@final
class MixedSpec(Controller[PydanticSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _modify_spec(cls) -> ModifyAnyCallable:
        return modify(status_code=cls.status_code)

    @classmethod
    def _validate_spec(cls) -> ValidateAnyCallable:
        return validate(ResponseSpec(int, status_code=cls.status_code))

    validate.lazy(_modify_spec)  # type: ignore[type-var]  # ty: ignore[invalid-argument-type]
    modify.lazy(_validate_spec)  # type: ignore[type-var]  # ty: ignore[invalid-argument-type]
