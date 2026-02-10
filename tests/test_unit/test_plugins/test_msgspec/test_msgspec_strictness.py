import json
from http import HTTPStatus
from typing import final

import pytest

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from django.http import HttpResponse
from inline_snapshot import snapshot

from django_modern_rest import Body, Controller
from django_modern_rest.plugins.msgspec import MsgspecSerializer
from django_modern_rest.serializer import SerializerContext
from django_modern_rest.test import DMRRequestFactory


@final
class _InputModel(msgspec.Struct):
    first_field: int
    second_field: int


@final
class _DefaultInputController(
    Controller[MsgspecSerializer],
    Body[_InputModel],
):
    def post(self) -> _InputModel:
        return self.parsed_body


def test_default_input_strictness_lax(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that default input validation is lax."""
    request = dmr_rf.post(
        '/whatever/',
        data={'first_field': '1', 'second_field': 1},
    )
    response = _DefaultInputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == snapshot(
        {'first_field': 1, 'second_field': 1},
    )


@final
class _OutputModel(msgspec.Struct):
    output_value: int


@final
class _DefaultOutputController(Controller[MsgspecSerializer]):
    def post(self) -> _OutputModel:
        # Returning a string "1" for an int field.
        # If strict=True (default for output), this should fail.
        # If strict=False, this would coerce to 1.
        return {'output_value': '1'}  # type: ignore[return-value]


def test_default_output_is_strict(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that default output validation is strict."""
    request = dmr_rf.post('/whatever/')
    response = _DefaultOutputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Expected `int`, got `str` - at `$.output_value`',
                'type': 'value_error',
            },
        ],
    })


@final
class _StrictContext(SerializerContext):
    strict_validation = True


@final
class _ExplicitStrictInputController(
    Controller[MsgspecSerializer],
    Body[_InputModel],
):
    serializer_context_cls = _StrictContext

    def post(self) -> _InputModel:
        raise NotImplementedError


def test_explicit_input_strictness(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that user can enable strict validation for inputs."""
    request = dmr_rf.post(
        '/whatever/',
        data={'first_field': '1', 'second_field': 1},
    )
    response = _ExplicitStrictInputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Expected `int`, got `str` - at `$.parsed_body.first_field`'
                ),
                'type': 'value_error',
            },
        ],
    })


@final
class _LaxContext(SerializerContext):
    strict_validation = False


@final
class _ExplicitLaxInputController(
    Controller[MsgspecSerializer],
    Body[_InputModel],
):
    serializer_context_cls = _LaxContext

    def post(self) -> _InputModel:
        return self.parsed_body


def test_explicit_input_laxness(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that user can enable lax validation for inputs."""
    request = dmr_rf.post(
        '/whatever/',
        data={'first_field': '1', 'second_field': '1'},
    )
    response = _ExplicitLaxInputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == snapshot(
        {'first_field': 1, 'second_field': 1},
    )
