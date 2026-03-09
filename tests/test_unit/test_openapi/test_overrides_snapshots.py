import json
from typing import Generic, TypedDict, TypeVar

import pydantic
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.openapi import OpenAPIContext, build_schema, default_config
from dmr.openapi.objects import OpenAPIType, Schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _UserModel(pydantic.BaseModel):
    age: int


class _UserController(Controller[PydanticSerializer]):
    def post(self) -> _UserModel:
        raise NotImplementedError


def test_regular_type_override(snapshot: SnapshotAssertion) -> None:
    """Ensure that regular type can be overriden."""
    context = OpenAPIContext(config=default_config())
    context.register_schema(
        _UserModel,
        Schema(type=OpenAPIType.OBJECT, title='_CustomTitleForUserModel1'),
    )

    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/user', _UserController.as_view())],
                    prefix='/api/v1',
                ),
                context=context,
            ).convert(),
            indent=2,
        )
        == snapshot
    )


def test_returns_reference(snapshot: SnapshotAssertion) -> None:
    """Ensure that overrides can return references."""
    context = OpenAPIContext(config=default_config())
    context.register_schema(
        _UserModel,
        lambda annotation, origin, type_args, **kwargs: (
            context.registries.schema.register(
                schema_name='_UserModel',
                schema=Schema(
                    title='_CustomTitleForUserModel2',
                    type=OpenAPIType.OBJECT,
                ),
                annotation=_UserModel,
            )
        ),
    )

    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/user', _UserController.as_view())],
                    prefix='/api/root/custom',
                ),
                context=context,
            ).convert(),
            indent=2,
        )
        == snapshot
    )


_GenericT = TypeVar('_GenericT')


class _GenericModel(TypedDict, Generic[_GenericT]):
    age: _GenericT


class _GenericController(Controller[PydanticSerializer]):
    def post(self) -> _GenericModel[int]:
        raise NotImplementedError


def test_generic_type_override(snapshot: SnapshotAssertion) -> None:
    """Ensure that generic type can be overriden."""
    context = OpenAPIContext(config=default_config())
    context.register_schema(
        _GenericModel,
        lambda annotation, origin, type_args, **kwargs: Schema(
            title='_GenericModel',
            type=OpenAPIType.OBJECT,
            additional_properties=context.generators.schema(
                type_args[0],
                PydanticSerializer,
            ),
        ),
    )

    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/generic', _GenericController.as_view())],
                    prefix='/api',
                ),
                context=context,
            ).convert(),
            indent=2,
        )
        == snapshot
    )
