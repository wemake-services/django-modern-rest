from collections.abc import Callable, Coroutine
from http import HTTPStatus
from typing import Any, assert_type, final

from django.contrib.auth.decorators import login_required
from django.views.decorators.debug import sensitive_post_parameters

from dmr import Body, Controller, modify
from dmr.decorators import endpoint_decorator
from dmr.plugins.pydantic import PydanticSerializer


@final
class _MySyncController(Controller[PydanticSerializer]):
    @endpoint_decorator(sensitive_post_parameters())
    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self, parsed_body: Body[str], /) -> None:
        return None


assert_type(_MySyncController.post, Callable[[_MySyncController, str], None])


@final
class _MyAsyncController(Controller[PydanticSerializer]):
    @endpoint_decorator(login_required(login_url='./test/login/'))
    @modify(status_code=HTTPStatus.NO_CONTENT)
    async def put(self, parsed_body: Body[str], /) -> None:
        return None


assert_type(
    _MyAsyncController.put,  # pyright: ignore[reportAssertTypeFailure]
    # mypy and pyright disagree on `Coroutine` vs `CoroutineType`
    Callable[[_MyAsyncController, str], Coroutine[Any, Any, None]],
)
