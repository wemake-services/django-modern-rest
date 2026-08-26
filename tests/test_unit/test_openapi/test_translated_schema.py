import json
from http import HTTPStatus

from django.http import HttpResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _
from syrupy.assertion import SnapshotAssertion

from dmr import (
    Controller,
    CookieSpec,
    HeaderSpec,
    ResponseSpec,
    validate,
)
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import Router


class _GetUserController(Controller[PydanticFastSerializer]):
    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            description=_('Response descr'),
            headers={'X-Translated': HeaderSpec(description=_('Header descr'))},
            cookies={
                'translated-cookie': CookieSpec(description=_('Cookie descr')),
            },
        ),
        summary=_('Validate sum'),
        description=_('Validated descr'),
    )
    def get(self) -> HttpResponse:
        raise NotImplementedError


def test_user_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for user controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path('user/', _GetUserController.as_view()),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
