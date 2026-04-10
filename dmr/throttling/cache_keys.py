from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


def remote_address(
    endpoint: 'Endpoint',
    controller: 'Controller[BaseSerializer]',
) -> str | None:
    return controller.request.META.get('REMOTE_ADDR')
