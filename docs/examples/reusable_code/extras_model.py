import dataclasses
from typing import Self

from typing_extensions import Sentinel, override

from dmr.controller import Controller
from dmr.endpoint import Extras
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
        from_endpoint: Self | Sentinel,
        from_controller: Self,
        controller_cls: type[Controller[BaseSerializer]],
        builder: EndpointMetadataBuilder,
    ) -> str:
        merger = builder.merger('response_text')
        return merger.not_empty(
            merger.first_set(
                (
                    EMPTY
                    if isinstance(from_endpoint, Sentinel)
                    else from_endpoint.response_text
                ),
                from_controller.response_text,
                'default_response',
            ),
        )
