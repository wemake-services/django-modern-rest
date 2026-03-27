from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse

from dmr import Controller, Path
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _PathModel(pydantic.BaseModel):
    user_id: int


@final
class _PathController(
    Controller[PydanticSerializer],
):
    def get(self, parsed_path: Path[_PathModel]) -> _PathModel:
        return parsed_path


def test_path_kwargs_only(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that named path parameters (kwargs only) work as before."""
    request = dmr_rf.get('/users/1')

    response = _PathController.as_view()(request, user_id=1)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


_StrArgs = tuple[str, ...]
_ArgsRoot = tuple[_StrArgs, dict[str, str]]


class _ArgsPathModel(pydantic.RootModel[_ArgsRoot]):
    """Path model accepting unnamed args with empty kwargs."""


@final
class _ArgsPathController(
    Controller[PydanticSerializer],
):
    def get(self, parsed_path: Path[_ArgsPathModel]) -> list[str]:
        args, _kwargs = parsed_path.root
        return list(args)


def test_path_unnamed_args(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that unnamed path parameters (args) are parsed as a tuple."""
    request = dmr_rf.get('/users/42/posts/7')

    response = _ArgsPathController.as_view()(request, '42', '7')

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


class _ArgsKwargsModel(pydantic.BaseModel):
    user_id: int


class _MixedPathModel(
    pydantic.RootModel[tuple[tuple[str, ...], _ArgsKwargsModel]],
):
    """Path model that accepts both unnamed args and named kwargs."""


@final
class _MixedPathController(
    Controller[PydanticSerializer],
):
    def get(self, parsed_path: Path[_MixedPathModel]) -> dict[str, object]:
        args, kwargs_model = parsed_path.root
        return {'args': list(args), 'user_id': kwargs_model.user_id}


def test_path_args_and_kwargs(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that both args and kwargs are returned when args is set."""
    request = dmr_rf.get('/extra/42/users/10')

    response = _MixedPathController.as_view()(
        request,
        'extra',
        '42',
        user_id='10',
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


_IntArgs = tuple[int, ...]
_IntArgsRoot = tuple[_IntArgs, dict[str, str]]


class _IntArgsPathModel(
    pydantic.RootModel[_IntArgsRoot],
):
    """Path model that coerces unnamed args to ints."""


@final
class _IntArgsPathController(
    Controller[PydanticSerializer],
):
    def get(self, parsed_path: Path[_IntArgsPathModel]) -> list[int]:
        args, _kwargs = parsed_path.root
        return list(args)


def test_path_args_coercion(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that unnamed string args can be coerced to ints via the model."""
    request = dmr_rf.get('/items/1/2/3')

    response = _IntArgsPathController.as_view()(request, '1', '2', '3')

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
