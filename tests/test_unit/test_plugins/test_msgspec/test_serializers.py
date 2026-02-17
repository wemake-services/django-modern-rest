from http import HTTPStatus
from typing import Any

import pytest
from django.http import HttpResponse
from faker import Faker

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)


from dmr import Body, Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.test import DMRRequestFactory


class _ForTestError(Exception):
    """Testing as custom error from built-in exception."""


class _ForTestMsgSpecError(msgspec.ValidationError):
    """Testing as custom error from msgspec.ValidationError."""


class _MsgSpecUserModel(msgspec.Struct):
    email: str


class _UserController(
    Controller[MsgspecSerializer],
    Body[_MsgSpecUserModel],
):
    """Blueprint for POST endpoint (with body)."""

    def post(self) -> _MsgSpecUserModel:
        return _MsgSpecUserModel(email=self.parsed_body.email)


def test_serializer_via_endpoint(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Try to serialize via endpoint."""
    email = faker.email()
    post_request = dmr_rf.post('/whatever/', data={'email': email})
    response = _UserController.as_view()(post_request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content


@pytest.mark.parametrize(
    ('err', 'is_raise'),
    [
        (msgspec.ValidationError(), False),
        (_ForTestMsgSpecError(), False),
        ('', True),
        (Exception(), True),
        (_ForTestError(), True),
        (1, True),
    ],
)
def test_serialize_errors_types(
    err: Any,
    is_raise: bool,  # noqa: FBT001
) -> None:
    """Ensures that MsgspecSerializer can serialize errors."""
    if is_raise:
        with pytest.raises(NotImplementedError):
            MsgspecSerializer().serialize_validation_error(err)
    else:
        assert MsgspecSerializer().serialize_validation_error(err)
