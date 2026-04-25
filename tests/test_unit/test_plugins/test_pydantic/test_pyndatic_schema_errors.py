from typing import Final

import pydantic
import pytest
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema as cs
from typing_extensions import override

from dmr import Controller
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import Router, path

_ERR_MSG: Final = 'from __get_pydantic_json_schema__'


class _NotModel(pydantic.BaseModel):
    email: str

    @classmethod
    @override
    def __get_pydantic_json_schema__(
        cls,
        core_schema: cs.CoreSchema,
        handler: pydantic.GetJsonSchemaHandler,  # noqa: WPS110
    ) -> JsonSchemaValue:
        raise TypeError(_ERR_MSG)


class _ControllerWithNotModel(Controller[PydanticFastSerializer]):
    async def get(self) -> _NotModel:
        raise NotImplementedError


def test_schema_error_contains_original_error() -> None:
    """Ensures that errors from schema generation are propagated."""
    router = Router(
        'api/v1/',
        [path('/whatever', _ControllerWithNotModel.as_view())],
    )

    with pytest.raises(
        UnsolvableAnnotationsError,
        match='Cannot generate OpenAPI schema',
    ) as exc:
        build_schema(router).convert()

    assert isinstance(exc.value.__cause__, TypeError)
    assert _ERR_MSG in str(exc.value.__cause__)


def test_schema_error_name() -> None:
    """Ensures that schema name does not error out."""
    assert (
        PydanticFastSerializer.schema_generator.schema_name(_NotModel) is None
    )
