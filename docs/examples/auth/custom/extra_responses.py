from collections.abc import Mapping
from http import HTTPStatus

from typing_extensions import override

from dmr import Controller
from dmr.metadata import EndpointMetadata, ResponseSpec
from dmr.security.base import unauth_response_spec
from dmr.serializer import BaseSerializer
from examples.auth.custom.auth import ProxyHeaderSyncAuth


class SignedProxyHeaderSyncAuth(ProxyHeaderSyncAuth):
    __slots__ = ()

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type[Controller[BaseSerializer]],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        return [
            # Keep the `401` that every auth declares:
            *self._add_new_response(
                unauth_response_spec(controller_cls),
                existing_responses,
            ),
            *self._add_new_response(
                ResponseSpec(
                    controller_cls.error_model,
                    status_code=HTTPStatus.FORBIDDEN,
                    description='Raised when the proxy signature is invalid',
                ),
                existing_responses,
            ),
        ]
