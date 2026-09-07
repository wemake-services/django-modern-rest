from http import HTTPStatus
from typing import ClassVar, TypeVar

from django.http import HttpResponse

from dmr import Controller, ResponseSpec, validate
from dmr.endpoint import ValidateAnyCallable
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)


class LoginController(Controller[_SerializerT]):
    status_code: ClassVar[HTTPStatus] = HTTPStatus.IM_USED

    @classmethod
    def lazy_spec(cls) -> ValidateAnyCallable:
        return validate(ResponseSpec(str, status_code=cls.status_code))

    @validate.lazy(lazy_spec)
    def get(self) -> HttpResponse:
        return self.to_response('login', status_code=self.status_code)
