import json
from http import HTTPStatus
from typing import TypeAlias, final

import pydantic
from django.http import HttpResponse

from dmr import Controller, Path
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _PathModel(pydantic.BaseModel):
    user_id: int


@final
class _PathController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_PathModel]) -> _PathModel:
        return parsed_path


def test_path_kwargs_only(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that named path parameters (kwargs only) work as before."""
    request = dmr_rf.get('/users/1')

    response = _PathController.as_view()(request, user_id=1)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'user_id': 1}


_StrArgs: TypeAlias = tuple[str, ...]
_ArgsModel: TypeAlias = pydantic.RootModel[_StrArgs]


@final
class _ArgsPathController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_ArgsModel]) -> list[str]:
        return list(parsed_path.root)


def test_path_unnamed_args(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that unnamed path parameters (args) are parsed."""
    request = dmr_rf.get('/users/42/posts/7')

    response = _ArgsPathController.as_view()(request, '42', '7')

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == ['42', '7']


_IntArgs: TypeAlias = tuple[int, ...]
_IntArgsModel: TypeAlias = pydantic.RootModel[_IntArgs]


@final
class _IntArgsPathController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_IntArgsModel]) -> list[int]:
        return list(parsed_path.root)  # pragma: no cover


def test_path_args_invalid(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that non-numeric args fail int coercion."""
    request = dmr_rf.get('/items/a/b/c')

    response = _IntArgsPathController.as_view()(
        request,
        'a',
        'b',
        'c',
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers['Content-Type'] == 'application/json'
