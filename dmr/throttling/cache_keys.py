import abc
import dataclasses
from typing import TYPE_CHECKING

from typing_extensions import override

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


class BaseThrottleCacheKey:
    runs_before_auth: bool
    name: str

    @abc.abstractmethod
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None: ...


@dataclasses.dataclass(slots=True, frozen=True)
class RemoteAddr(BaseThrottleCacheKey):
    runs_before_auth: bool = True
    name: str = 'RemoteAddr'

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        return controller.request.META.get('RemoteAddr')
