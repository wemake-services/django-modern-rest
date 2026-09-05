from http import HTTPStatus
from typing import Final

from dmr import ResponseSpec
from dmr.errors import ErrorModel
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session.views import (
    DjangoSessionAsyncController,
    DjangoSessionPayload,
    DjangoSessionResponse,
    DjangoSessionSyncController,
)
from dmr.security.token.views import (
    ObtainTokenAsyncController,
    ObtainTokenPayload,
    ObtainTokenResponse,
    ObtainTokenSyncController,
)

# Controllers we ship must not narrow `responses` to a fixed-size tuple,
# otherwise no subclass can add a spec of its own.
_SERVER_ERROR: Final = ResponseSpec(
    return_type=ErrorModel,
    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
)


class ExtendedTokenController(
    ObtainTokenSyncController[
        PydanticSerializer,
        ObtainTokenPayload,
        ObtainTokenResponse,
    ],
):
    responses = (*ObtainTokenSyncController.responses, _SERVER_ERROR)


class ExtendedSessionController(
    DjangoSessionSyncController[
        PydanticSerializer,
        DjangoSessionPayload,
        DjangoSessionResponse,
    ],
):
    responses = (*DjangoSessionSyncController.responses, _SERVER_ERROR)


class ExtendedAsyncTokenController(
    ObtainTokenAsyncController[
        PydanticSerializer,
        ObtainTokenPayload,
        ObtainTokenResponse,
    ],
):
    responses = (*ObtainTokenAsyncController.responses, _SERVER_ERROR)


class ExtendedAsyncSessionController(
    DjangoSessionAsyncController[
        PydanticSerializer,
        DjangoSessionPayload,
        DjangoSessionResponse,
    ],
):
    responses = (*DjangoSessionAsyncController.responses, _SERVER_ERROR)
