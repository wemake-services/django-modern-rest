from abc import abstractmethod
from http import HTTPStatus
from typing import Generic, TypeVar

from django.http import HttpResponse

from dmr import Body, Controller, ResponseSpec, validate
from dmr.serializer import BaseSerializer
from dmr.types import safe_typevar

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)
_RequestModelT = TypeVar('_RequestModelT')
_ResponseBodyT = TypeVar('_ResponseBodyT')


class ReusableController(
    Controller[_SerializerT],
    Generic[_SerializerT, _RequestModelT, _ResponseBodyT],
):
    @validate(
        ResponseSpec(
            safe_typevar('_ResponseBodyT'),
            status_code=HTTPStatus.CREATED,
        ),
    )
    def post(self, parsed_body: Body[_RequestModelT]) -> HttpResponse:
        return self.to_response(self.convert(parsed_body))

    @abstractmethod
    def convert(self, parsed_body: _RequestModelT) -> _ResponseBodyT:
        raise NotImplementedError
