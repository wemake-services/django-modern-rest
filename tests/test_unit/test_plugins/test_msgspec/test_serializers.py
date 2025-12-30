import sys
from http import HTTPStatus
from typing import final

import pytest
from django.http import HttpResponse
from faker import Faker

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)


from django_modern_rest import Blueprint, Body, Controller
from django_modern_rest.plugins.msgspec import MsgspecSerializer
from django_modern_rest.test import DMRRequestFactory


class _ForTestError(Exception):
    """Testing as custom error from built-in exception."""


class _ForTestMsgSpecError(msgspec.ValidationError):
    """Testing as custom error from msgspec.ValidationError."""


class _MsgSpecUserModel(msgspec.Struct):
    email: str


class _UserGetBlueprint(Blueprint[MsgspecSerializer]):
    """Blueprint for GET endpoint (without body)."""

    def get(self) -> _MsgSpecUserModel:
        return _MsgSpecUserModel(email='email@test.edu')


class _UserPostBlueprint(
    Blueprint[MsgspecSerializer],
    Body[_MsgSpecUserModel],
):
    """Blueprint for POST endpoint (with body)."""

    def post(self) -> _MsgSpecUserModel:
        return _MsgSpecUserModel(email=self.parsed_body.email)


@final
class _UserController(Controller[MsgspecSerializer]):
    blueprints = [_UserGetBlueprint, _UserPostBlueprint]


@pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason='3.14 does not fully support msgspec yet',
)
def test_serializer_via_endpoint(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Try to serialize via endpoint."""
    email = faker.email()
    post_request = dmr_rf.post('/whatever/', data={'email': email})
    response = _UserController.as_view()(post_request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, f'post: {response=}'


@pytest.mark.parametrize(
    ('err', 'is_raise'),
    [
        ('', False),
        (Exception(), True),
        (_ForTestError(), True),
        (msgspec.ValidationError(), False),
        (_ForTestMsgSpecError(), False),
        (1, True),
    ],
)
def test_serialize_errors_types(
    err: str | Exception,
    is_raise: bool,  # noqa: FBT001
) -> None:
    """Ensures that MsgspecSerializer can serialize errors."""
    if is_raise:
        with pytest.raises(NotImplementedError):
            MsgspecSerializer().error_serialize(err)
    else:
        assert MsgspecSerializer().error_serialize(err)
