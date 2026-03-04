import re

import pytest
from django.urls import path
from syrupy.assertion import SnapshotAssertion
from typing_extensions import override

try:
    from openapi_spec_validator.validation.exceptions import (
        OpenAPIValidationError,
    )
except ImportError:  # pragma: no cover
    pytest.skip(
        reason='openapi_spec_validator is not installed',
        allow_module_level=True,
    )

from dmr import Controller, modify
from dmr.endpoint import Endpoint
from dmr.openapi import build_schema
from dmr.openapi.objects import Components, SecurityRequirement, SecurityScheme
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.security import SyncAuth
from dmr.serializer import BaseSerializer


class _WrongAuth(SyncAuth):
    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> None:
        raise NotImplementedError

    @property
    @override
    def security_scheme(self) -> Components:
        return Components(
            security_schemes={
                'wrong': SecurityScheme(
                    type='http',
                    name='Wrong',
                ),
            },
        )

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        return SecurityRequirement()


class _UserController(
    Controller[PydanticSerializer],
):
    @modify(auth=[_WrongAuth()])
    def post(self) -> str:
        raise NotImplementedError


def test_schema_validation(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is validated correctly."""
    with pytest.raises(
        OpenAPIValidationError,
        match=re.escape('instance["components"]["securitySchemes"]["wrong"]'),
    ):
        build_schema(
            Router(
                [path('/user', _UserController.as_view())],
                prefix='/api/v1',
            ),
        ).convert()
