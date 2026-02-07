from typing import TypeVar

from typing_extensions import TypedDict

from django_modern_rest import Controller
from django_modern_rest.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)


class _ResponseBody(TypedDict):
    message: str


class ReusableController(Controller[_SerializerT]):
    def get(self) -> _ResponseBody:
        serializer_name = self.serializer.__name__
        return {'message': f'hello from {serializer_name}'}
