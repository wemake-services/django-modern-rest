from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Concatenate, TypeVar, overload

import pydantic
from django.http import HttpRequest, HttpResponse
from typing_extensions import ParamSpec

from django_modern_rest.plugins.pydantic.serialization import model_dump_json

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller

_ParamT = ParamSpec('_ParamT')
_SelfT = TypeVar('_SelfT', bound='Controller')
_ModelT = TypeVar('_ModelT', bound=pydantic.BaseModel)


@overload
def rest(
    method: Callable[Concatenate[_SelfT, _ParamT], _ModelT],
    /,
) -> Callable[Concatenate[_SelfT, HttpRequest, _ParamT], HttpResponse]: ...


@overload
def rest(  # noqa: WPS234
    *,
    return_dto: type[pydantic.BaseModel],
    # TODO: add schema modifications here
) -> Callable[
    [
        Callable[Concatenate[_SelfT, _ParamT], HttpResponse],
    ],
    Callable[Concatenate[_SelfT, HttpRequest, _ParamT], HttpResponse],
]: ...


def rest(
    method: Callable[Concatenate[_SelfT, _ParamT], _ModelT] | None = None,
    /,
    *,
    return_dto: type[pydantic.BaseModel] | None = None,
) -> (
    Callable[Concatenate[_SelfT, HttpRequest, _ParamT], HttpResponse]
    | Callable[
        [
            Callable[Concatenate[_SelfT, _ParamT], HttpResponse],
        ],
        Callable[Concatenate[_SelfT, HttpRequest, _ParamT], HttpResponse],
    ]
):
    """
    Decorator for REST endpoints.

    When *return_dto* is passed, it means that we return
    an instance of :class:`django.http.HttpResponse` or its subclass.
    But, we still want to show the response type in OpenAPI schema
    and also want to do an extra round of validation
    to be sure that it fits the schema.
    """
    if method is not None:

        @wraps(method)
        def decorator(  # noqa: WPS430
            self: _SelfT,
            request: HttpRequest,
            /,
            *args: _ParamT.args,
            **kwargs: _ParamT.kwargs,
        ) -> HttpResponse:
            model = method(self, *args, **kwargs)
            return HttpResponse(
                model_dump_json(model, self.return_dto_kwargs),
                content_type='application/json',
            )

        return decorator

    def factory(
        method: Callable[Concatenate[_SelfT, _ParamT], HttpResponse],
    ) -> Callable[Concatenate[_SelfT, HttpRequest, _ParamT], HttpResponse]:
        @wraps(method)
        def decorator(
            self: _SelfT,
            request: HttpRequest,
            /,
            *args: _ParamT.args,
            **kwargs: _ParamT.kwargs,
        ) -> HttpResponse:
            # TODO: validate `HttpResponse.content` with `return_dto`
            # TODO: support `StreamingHttpResponse`
            # TODO: support `JsonResponse`
            # TODO: use `return_dto` for schema generation
            # TODO: use configurable `json` encoders and decoders
            # TODO: make sure `return_dto` validation
            # can be turned off for production
            return method(self, *args, **kwargs)

        return decorator

    return factory
