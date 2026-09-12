from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt.views import VerifyTokenPayload, VerifyTokenSyncController


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


# run: {"controller": "VerifySyncController", "method": "post", "url": "/api/auth/verify/", "body": {"access_token": "$JWT_ACCESS_TOKEN"}, "populate_db": true, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "VerifySyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
