from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.views import (
    VerifyTokenPayload,
    VerifyTokenSyncController,
)


# You can also use `VerifyTokenAsyncController` if needed:
class VerifySyncController(
    VerifyTokenSyncController[
        PydanticSerializer,
        VerifyTokenPayload,
    ],
):
    @override
    def convert_verify_payload(self, payload: VerifyTokenPayload) -> str:
        return payload['access_token']


# openapi: {"controller": "VerifySyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
