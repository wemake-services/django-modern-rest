from http import HTTPStatus

from django.http import HttpResponse

from dmr import Controller, ResponseSpec, modify, validate
from dmr.internal.endpoint import ModifySyncCallable, ValidateSyncCallable
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.django_session import (
    DjangoSessionSyncAuth,
)


class My(Controller[PydanticFastSerializer]):
    status_code = HTTPStatus.OK

    @classmethod
    def _modify_spec(cls) -> ModifySyncCallable:
        return modify(
            status_code=cls.status_code,
            auth=[DjangoSessionSyncAuth()],
        )

    @modify.lazy(_modify_spec)
    def get(self) -> dict[str, str]: ...

    @modify(auth=[DjangoSessionSyncAuth()])
    def post(self) -> str: ...

    @classmethod
    def _validate_spec(cls) -> ValidateSyncCallable:
        return validate(
            ResponseSpec(str, status_code=cls.status_code),
            auth=[DjangoSessionSyncAuth()],
        )

    @validate.lazy(_validate_spec)
    def put(self) -> HttpResponse: ...


metadata = My.api_endpoints['PUT'].metadata
print(metadata.responses[My.status_code])
