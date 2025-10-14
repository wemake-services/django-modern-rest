from http import HTTPStatus

import pydantic
from django.http import HttpResponse, JsonResponse

from django_modern_rest import Controller, modify, validate
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _Model(pydantic.BaseModel):
    field: str


class _CorrectModifyController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.OK)
    def get(self) -> str:
        return 'Done'

    @modify(status_code=HTTPStatus.OK)
    async def post(self) -> int:
        return 1

    @modify()  # no args
    async def put(self) -> int:
        return 1


class _CorrectValidateController(Controller[PydanticSerializer]):
    @validate(status_code=HTTPStatus.OK, return_type=_Model)
    def get(self) -> HttpResponse:
        return HttpResponse()

    @validate(return_type=list[int], status_code=HTTPStatus.OK)
    async def post(self) -> JsonResponse:
        return JsonResponse([])


class _WrongModifyController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.OK)  # type: ignore[deprecated]
    def get(self) -> JsonResponse:
        return JsonResponse([])

    @modify(status_code=HTTPStatus.OK)  # type: ignore[deprecated]
    async def post(self) -> HttpResponse:
        return HttpResponse()

    @modify()  # type: ignore[deprecated]
    def put(self) -> HttpResponse:
        return HttpResponse()


class _WrongValidateController(Controller[PydanticSerializer]):
    @validate(status_code=HTTPStatus.OK, return_type=_Model)  # type: ignore[type-var]
    def get(self) -> int:
        return 1

    @validate(return_type=list[int], status_code=HTTPStatus.OK)  # type: ignore[type-var]
    async def post(self) -> str:
        return 'a'

    # Not enough params:
    @validate(return_type=list[int])  # type: ignore[call-arg]
    async def put(self) -> JsonResponse:
        return JsonResponse([])
