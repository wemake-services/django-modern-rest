import dataclasses
from typing import Final, Self

from typing_extensions import Sentinel, override

from dmr.controller import Controller
from dmr.endpoint import (
    Endpoint,
    Extras,
    ModifyEndpoint,
    request_endpoint,
)
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.serializer import BaseSerializer
from dmr.types import EMPTY
from dmr.validation import EndpointMetadataBuilder


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class SmartResponse(Extras[str]):
    response_text: str | Sentinel = EMPTY

    @classmethod
    @override
    def build(
        cls,
        payload_extras: Self | Sentinel,
        controller_cls: type[Controller[BaseSerializer]],
        builder: EndpointMetadataBuilder,
    ) -> str:
        merger = builder.merger('response_text')
        return merger.not_empty(
            merger.first_set(
                (
                    EMPTY
                    if isinstance(payload_extras, Sentinel)
                    else payload_extras.response_text
                ),
                getattr(controller_cls, 'response_text', EMPTY),
                'default_response',
            ),
        )


#: Same as :data:`dmr.modify`, but supports ``extras=SmartResponse(...)``.
modify: Final = ModifyEndpoint[SmartResponse]()


class _CustomEndpoint(Endpoint):
    extras_cls = SmartResponse


class APIController(Controller[PydanticFastSerializer]):
    endpoint_cls = _CustomEndpoint
    response_text = 'from controller'

    def get(self) -> str:
        return request_endpoint(self.request).metadata.extras


# run: {"controller": "APIController", "method": "get", "url": "/api/example/"}  # noqa: ERA001
# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
