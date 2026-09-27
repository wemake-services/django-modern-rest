from http import HTTPStatus

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from typing_extensions import override

from dmr import ResponseSpec, modify
from dmr.endpoint import ModifyAnyCallable
from dmr.errors import ErrorModel
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.base import NO_STORE_HEADERS
from dmr.security.jwt.views import (
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
)
from dmr.test import DMRRequestFactory


class _BrokenAlgorithmController(
    ObtainTokensSyncController[
        PydanticFastSerializer,
        ObtainTokensPayload,
        ObtainTokensResponse,
    ],
):
    # There is no such algorithm, `pyjwt` will refuse to sign the token:
    jwt_algorithm = 'nope'

    # The views we ship don't declare `500` themselves,
    # and response validation only allows declared status codes.
    # Endpoint responses override controller ones, so we extend the spec:
    @classmethod
    @override
    def modify_spec(cls) -> ModifyAnyCallable:
        return modify(
            status_code=cls.response_status_code,
            extra_responses=[
                ResponseSpec(
                    return_type=cls.error_model,
                    status_code=HTTPStatus.UNAUTHORIZED,
                ),
                ResponseSpec(
                    return_type=ErrorModel,
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                ),
            ],
            headers=NO_STORE_HEADERS,
        )

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload

    @override
    def make_api_response(self) -> ObtainTokensResponse:
        return {
            'access_token': self.create_jwt_token(
                token_type='access',  # noqa: S106
            ),
            'refresh_token': self.create_jwt_token(
                token_type='refresh',  # noqa: S106
            ),
        }


@pytest.mark.django_db
def test_token_we_cannot_sign_is_a_server_error(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures that views convert `JWTokenError` into a `500` response."""
    request = dmr_rf.post(
        '/whatever/',
        data={'username': admin_user.username, 'password': 'password'},
        content_type='application/json',
    )

    response = _BrokenAlgorithmController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR, (
        response.content
    )
