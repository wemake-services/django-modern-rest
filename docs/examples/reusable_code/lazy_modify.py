from http import HTTPStatus
from typing import ClassVar

from dmr import Controller, modify
from dmr.endpoint import ModifyAnyCallable
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)


class LoginController(Controller[_SerializerT]):
    status_code: ClassVar[HTTPStatus] = HTTPStatus.IM_USED

    @classmethod
    def lazy_spec(cls) -> ModifyAnyCallable:
        return modify(status_code=cls.status_code)

    @modify.lazy(lazy_spec)
    def get(self) -> str:
        return 'login'
