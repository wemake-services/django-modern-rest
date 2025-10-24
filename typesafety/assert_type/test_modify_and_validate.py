from http import HTTPStatus

import pydantic
from django.http import HttpResponse, JsonResponse

from django_modern_rest import (
    Controller,
    Endpoint,
    HeaderDescription,
    NewHeader,
    ResponseDescription,
    modify,
    validate,
)
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

    @modify(headers={'X-Custom': NewHeader(value='Example')})
    def patch(self) -> int:
        return 1

    @modify()  # no args
    async def put(self) -> int:
        return 1


class _CorrectValidateController(Controller[PydanticSerializer]):
    def endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        return JsonResponse([])

    @validate(
        ResponseDescription(status_code=HTTPStatus.OK, return_type=_Model),
        error_handler=endpoint_error,
    )
    def get(self) -> HttpResponse:
        return HttpResponse()

    async def async_endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        return JsonResponse([])

    @validate(
        ResponseDescription(return_type=list[int], status_code=HTTPStatus.OK),
        error_handler=async_endpoint_error,
    )
    async def post(self) -> JsonResponse:
        return JsonResponse([])

    @validate(
        ResponseDescription(
            return_type=list[int],
            status_code=HTTPStatus.OK,
            headers={'X-Custom': HeaderDescription()},
        ),
    )
    async def put(self) -> JsonResponse:
        return JsonResponse([])


class _WrongModifyController(Controller[PydanticSerializer]):
    async def async_endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        return JsonResponse([])

    @modify(  # type: ignore[type-var]
        status_code=HTTPStatus.OK,
        error_handler=async_endpoint_error,
    )
    def get(self) -> int:
        return 1

    def endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        return JsonResponse([])

    @modify(  # type: ignore[deprecated]
        status_code=HTTPStatus.OK,
        error_handler=endpoint_error,
    )
    async def post(self) -> int:
        return 1


class _WrongModifyErrorController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.OK)  # type: ignore[deprecated]
    def get(self) -> JsonResponse:
        return JsonResponse([])

    @modify(status_code=HTTPStatus.OK)  # type: ignore[deprecated]
    async def post(self) -> HttpResponse:
        return HttpResponse()

    @modify()  # type: ignore[deprecated]
    def put(self) -> HttpResponse:
        return HttpResponse()

    @modify(headers={'X-Custom': HeaderDescription()})  # type: ignore[dict-item]
    def patch(self) -> int:
        return 1


class _WrongValidateController(Controller[PydanticSerializer]):
    @validate(  # type: ignore[type-var]
        ResponseDescription(status_code=HTTPStatus.OK, return_type=_Model),
    )
    def get(self) -> int:
        return 1

    @validate(  # type: ignore[type-var]
        ResponseDescription(return_type=list[int], status_code=HTTPStatus.OK),
    )
    async def post(self) -> str:
        return 'a'

    # Not enough params:
    @validate(ResponseDescription(return_type=list[int]))  # type: ignore[call-arg]
    async def put(self) -> JsonResponse:
        return JsonResponse([])

    @validate(
        ResponseDescription(
            return_type=list[int],
            status_code=HTTPStatus.OK,
            headers={'X-Custom': NewHeader(value=1)},  # type: ignore[dict-item, arg-type]
        ),
    )
    def patch(self) -> JsonResponse:
        return JsonResponse([])

    @validate()  # type: ignore[call-overload, misc]
    async def delete(self) -> HttpResponse:
        return JsonResponse([])


class _WrongValidateErrorsController(Controller[PydanticSerializer]):
    async def async_endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        return JsonResponse([])

    @validate(  # type: ignore[arg-type]
        ResponseDescription(list[int], status_code=HTTPStatus.OK),
        error_handler=async_endpoint_error,
    )
    def get(self) -> HttpResponse:
        return JsonResponse([])

    def endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        return JsonResponse([])

    @validate(  # type: ignore[arg-type]
        ResponseDescription(list[int], status_code=HTTPStatus.OK),
        error_handler=endpoint_error,
    )
    async def post(self) -> HttpResponse:
        return JsonResponse([])
