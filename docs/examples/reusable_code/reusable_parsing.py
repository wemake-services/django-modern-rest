from abc import abstractmethod
from typing import Generic, TypeVar

from dmr import Body, Controller
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)
_RequestModelT = TypeVar('_RequestModelT')
_ResponseBodyT = TypeVar('_ResponseBodyT')


class ReusableController(
    Controller[_SerializerT],
    Body[_RequestModelT],
    Generic[_SerializerT, _RequestModelT, _ResponseBodyT],
):
    def post(self) -> _ResponseBodyT:
        return self.convert(self.parsed_body)

    @abstractmethod
    def convert(self, parsed_body: _RequestModelT) -> _ResponseBodyT:
        raise NotImplementedError
