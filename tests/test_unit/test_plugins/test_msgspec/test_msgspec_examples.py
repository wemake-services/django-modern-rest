from typing import Annotated

import pytest
from django.conf import LazySettings
from django.urls import path

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router
from dmr.settings import Settings


class _FieldExampleMsgspecModel(msgspec.Struct):
    username: Annotated[str, msgspec.Meta(examples=['admin'])]


class _FieldExampleMsgspecController(Controller[MsgspecSerializer]):
    def get(self) -> _FieldExampleMsgspecModel:
        raise NotImplementedError


def test_field_examples_used_model_example(
    settings: LazySettings,
) -> None:
    """Ensure msgspec Meta examples are used in generated model example."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1639
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 1}

    schema = build_schema(
        Router(
            'api/v1/',
            [path('user/', _FieldExampleMsgspecController.as_view())],
        ),
    ).convert()

    model_schema = schema['components']['schemas']['_FieldExampleMsgspecModel']
    assert model_schema['examples'] == [{'username': 'admin'}]
